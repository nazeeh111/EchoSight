"""Experimental empirical-direct-kernel sparse fit. No geometry or truth input."""
import numpy as np
from scipy.optimize import least_squares

def extract(observation, maximum=18):
    if observation['status']!='ok':return []
    description=observation['response'];response=np.array(description['values']);fs=description['sample_rate_hz']
    direct=-description['start_delay_s']*fs;axis=np.arange(len(response));radius=round(.0008*fs)
    grid=np.arange(-radius,radius+1);kernel=np.interp(direct+grid,axis,response);kernel/=max(abs(kernel))
    columns=[np.interp(axis-direct,grid,kernel,left=0,right=0)]
    residual=response-np.asarray(columns[0])*np.dot(response,columns[0])/np.dot(columns[0],columns[0])
    delays=[];coefficients=[];peaks=[]
    threshold=.07*max(abs(response));minimum=.00035*fs;resolution=2*fs/13000
    for _ in range(maximum):
        magnitude=abs(residual).copy();magnitude[axis<direct+minimum]=0
        for delay in delays:magnitude[abs(axis-direct-delay)<resolution]=0
        peak=int(np.argmax(magnitude))
        if magnitude[peak]<threshold:break
        from scipy.signal import find_peaks
        # Use a continuously shifted kernel and bounded joint refit of all paths.
        delta=peak-direct
        delays.append(delta)
        initial=np.array(delays)
        def matrix(ds):return np.array([columns[0]]+[np.interp(axis-direct-d,grid,kernel,left=0,right=0) for d in ds]).T
        def project(ds):
            A=matrix(ds);coef=np.linalg.lstsq(A,response,rcond=None)[0]
            return A,coef
        def error(ds):
            A,coef=project(ds);return A@coef-response
        fit=least_squares(error,initial,bounds=(initial-resolution/2,initial+resolution/2),max_nfev=15,ftol=1e-5,xtol=1e-5,gtol=1e-5)
        delays=list(fit.x);A,coefficients=project(delays);residual=response-A@coefficients
    out=[]
    if not len(delays):return out
    # Check the remaining signed waveform after jointly accounting for neighbors.
    # Half-energy criterion is fixed before evaluating this revision on real RIRs.
    for index,(d,a) in enumerate(zip(delays,coefficients[1:]),1):
        if abs(a)<threshold:continue
        near=abs(axis-direct-d)<=fs/13000
        isolated=residual+A[:,index]*a
        shape=float(np.linalg.norm(residual[near])/max(np.linalg.norm(isolated[near]),1e-20))
        out.append(dict(delay_s=float(d/fs),amplitude=float(abs(a/coefficients[0])),waveform_shape_residual=shape,unmodeled=shape>np.sqrt(.5)))
    return sorted(out,key=lambda c:c['delay_s'])
