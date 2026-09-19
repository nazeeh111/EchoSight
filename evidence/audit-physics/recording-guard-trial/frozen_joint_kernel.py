"""Experimental empirical-direct-kernel sparse fit. No geometry or truth input."""
import numpy as np
from scipy.optimize import least_squares

class FitCancelled(Exception): pass

def extract(observation, responses, bandwidth_hz, max_echo_delay_s, cancel=None, maximum=18):
    def check():
        if cancel and cancel():raise FitCancelled()
    check()
    if observation['status']!='ok':return [],{}
    description=observation['response'];response=np.array(description['values']);fs=description['sample_rate_hz']
    direct=-description['start_delay_s']*fs;axis=np.arange(len(response));radius=round(.0008*fs)
    if len(response)>round(.2*fs) or len(responses)>16:raise ValueError('Joint response exceeds allocation limit')
    grid=np.arange(-radius,radius+1);kernel=np.interp(direct+grid,axis,response);kernel/=max(abs(kernel))
    columns=[np.interp(axis-direct,grid,kernel,left=0,right=0)]
    residual=response-np.asarray(columns[0])*np.dot(response,columns[0])/np.dot(columns[0],columns[0])
    delays=[];coefficients=[];peaks=[]
    threshold=.07*max(abs(response));minimum=.00035*fs;resolution=2*fs/bandwidth_hz
    for _ in range(maximum):
        check()
        magnitude=abs(residual).copy();magnitude[axis<direct+minimum]=0
        magnitude[axis>direct+max_echo_delay_s*fs]=0
        for delay in delays:magnitude[abs(axis-direct-delay)<resolution]=0
        peak=int(np.argmax(magnitude))
        if magnitude[peak]<threshold:break
        # Use a continuously shifted kernel and bounded joint refit of all paths.
        delta=peak-direct
        delays.append(delta)
        initial=np.array(delays)
        def matrix(ds):return np.array([columns[0]]+[np.interp(axis-direct-d,grid,kernel,left=0,right=0) for d in ds]).T
        def project(ds):
            check()
            A=matrix(ds);coef=np.linalg.lstsq(A,response,rcond=None)[0]
            return A,coef
        def error(ds):
            A,coef=project(ds);return A@coef-response
        fit=least_squares(error,initial,bounds=(initial-resolution/2,initial+resolution/2),max_nfev=15,ftol=1e-5,xtol=1e-5,gtol=1e-5)
        delays=list(fit.x);A,coefficients=project(delays);residual=response-A@coefficients
    out=[]
    if not len(delays):return out,dict(iterations=0)
    # Fit repetition amplitudes and a first-order timing perturbation jointly.
    # These are conditional repeatability statistics, not source-model calibration.
    derivatives=[]
    for d in [0.]+delays:
        plus=np.interp(axis-direct-d-.05,grid,kernel,left=0,right=0)
        minus=np.interp(axis-direct-d+.05,grid,kernel,left=0,right=0)
        derivatives.append((plus-minus)/.1)
    derivative=np.asarray(derivatives).T
    repeat_coefficients=[];repeat_shifts=[]
    for repeat in responses:
        check()
        co=np.linalg.lstsq(A,repeat,rcond=None)[0]
        J=np.column_stack([A,derivative*co[None,:]])
        correction=np.linalg.lstsq(J,repeat-A@co,rcond=None)[0]
        repeat_coefficients.append(co+correction[:len(co)])
        repeat_shifts.append(correction[len(co):])
    repeat_coefficients=np.asarray(repeat_coefficients)
    repeat_shifts=np.asarray(repeat_shifts)
    relative_shifts=(repeat_shifts[:,1:]-repeat_shifts[:,:1])/fs
    scatter=np.cov(relative_shifts,rowvar=False,ddof=1)
    scatter=np.atleast_2d(scatter)
    timing_floor=max(.5/fs,.5/bandwidth_hz)
    # Check the remaining signed waveform after jointly accounting for neighbors.
    # Half-energy criterion is fixed before evaluating this revision on real RIRs.
    for index,(d,a) in enumerate(zip(delays,coefficients[1:]),1):
        if abs(a)<threshold:continue
        near=abs(axis-direct-d)<=fs/bandwidth_hz
        isolated=residual+A[:,index]*a
        shape=float(np.linalg.norm(residual[near])/max(np.linalg.norm(isolated[near]),1e-20))
        support=int(np.count_nonzero((np.abs(repeat_coefficients[:,index])>threshold*.65)&(np.abs(relative_shifts[:,index-1])*fs<resolution)))
        out.append(dict(delay_s=float(d/fs),amplitude=float(abs(a/coefficients[0])),waveform_shape_residual=shape,unmodeled=shape>np.sqrt(.5),
            repeat_support=support,repeat_count=len(responses),delay_std_s=max(timing_floor,float(np.sqrt(max(scatter[index-1,index-1],0))))))
    metadata=dict(iterations=len(delays),direct_kernel_half_width_s=.0008,
        model='signed shifted empirical direct kernel',timing_covariance_status='experimental conditional repeatability; kernel/systematic bias not calibrated',
        conditional_repeat_delay_covariance_s2=scatter.tolist(),covariance_delay_order_s=[float(d/fs) for d in delays],
        normalized_response_residual=float(np.linalg.norm(residual)/max(np.linalg.norm(response),1e-20)))
    return sorted(out,key=lambda c:c['delay_s']),metadata
