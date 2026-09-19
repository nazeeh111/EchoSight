"""Reference-reflector calibration; never infer a room from supplied reference truth."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares


def _jacobian(function, point):
    point = np.asarray(point, float)
    columns = []
    for i in range(len(point)):
        step = 1e-5 * max(1., abs(point[i]))
        delta = np.zeros(len(point)); delta[i] = step
        columns.append((function(point + delta) - function(point - delta)) / (2 * step))
    return np.column_stack(columns)


def calibrate_reference(session, reference):
    """Propose source/effective-speed calibration from original recordings.

    Reference plane and its uncertainty are independently surveyed inputs. Two
    disjoint capture sets must be declared before processing. Only one candidate
    in the physically allowed reference window is usable; no truth labels or
    best-looking validation subsets are selected. No session is changed here.
    """
    from .pipeline import process_session
    from .storage import load_session, validate_session
    session = load_session(session) if isinstance(session, (str, Path)) else validate_session(session)
    if not isinstance(reference, dict): raise ValueError('reference must be an object')
    normal = np.asarray(reference.get('normal'), float)
    if normal.shape != (3,) or not np.all(np.isfinite(normal)) or abs(np.linalg.norm(normal)-1) > 1e-6:
        raise ValueError('reference normal must be a finite unit vector')
    required = ('offset_m', 'offset_std_m', 'normal_std_rad')
    if any(k not in reference for k in required): raise ValueError('reference survey values and uncertainties are required')
    if session.get('source_position_m') is None: raise ValueError('nominal source pose is required')
    if any(c.get('receiver_position_m') is None for c in session['captures']): raise ValueError('receiver poses are required')
    offset = float(reference['offset_m'])
    offset_std = float(reference['offset_std_m'])
    angle_std = float(reference['normal_std_rad'])
    radius = float(reference.get('source_search_radius_m', .15))
    bounds = np.asarray(reference.get('effective_speed_bounds_m_s', [300.,380.]), float)
    if not np.isfinite(offset) or abs(offset)>1000 or not 0 < offset_std <= .05 or not 0 < angle_std <= .03:
        raise ValueError('reference must declare positive bounded survey uncertainties')
    if not .01 <= radius <= .5 or bounds.shape != (2,) or not np.all(np.isfinite(bounds)) or not 250 <= bounds[0] < bounds[1] <= 460:
        raise ValueError('invalid source search or effective speed bounds')
    train, held = reference.get('training_capture_ids'), reference.get('validation_capture_ids')
    if any(not isinstance(ids,list) or any(not isinstance(i,str) for i in ids) for ids in (train,held)):
        raise ValueError('declare disjoint training and validation capture IDs')
    if len(train)<8 or len(held)<4 or len(set(train+held)) != len(train+held):
        raise ValueError('need at least eight unique training and four held-out captures')
    captures = {c['capture_id']:c for c in session['captures']}
    if set(train+held) != set(captures): raise ValueError('partition every capture before processing; no unreported exclusions')
    source = np.asarray(session['source_position_m'],float)
    points = np.asarray([captures[c]['receiver_position_m'] for c in train+held],float)
    if np.any((points@normal-offset)*(source@normal-offset)<=0):
        raise ValueError('source and receivers must be on one side of reference plane')
    pairwise=np.linalg.norm(points[:,None,:]-points[None,:,:],axis=2)
    np.fill_diagonal(pairwise,np.inf)
    if np.min(pairwise)<.001:
        raise ValueError('training views must be distinct and validation poses held out spatially')
    # A receiver plane through the source cannot identify a source displacement
    # normal to that plane. The Jacobian guard below covers less obvious cases.
    if np.linalg.matrix_rank(points[:len(train)]-points[:len(train)].mean(axis=0),tol=1e-5)<3:
        return {'schema_version':'1.0','status':'rejected','diagnostics':['nonspatial_calibration_positions'], 'physical_validation':False}
    result=process_session(session)
    observations={o['capture_id']:o for o in result.get('observations',[])}
    image=source+2*(offset-normal@source)*normal
    nominal_lengths=np.linalg.norm(points-image,axis=1)-np.linalg.norm(points-source,axis=1)
    selected=[];failures=[]
    for i,cid in enumerate(train+held):
        observation=observations.get(cid,{})
        # The excess path is 2-Lipschitz in source position. A cube fit below is
        # restricted by an additional Euclidean-radius acceptance check.
        low=max(0.,(nominal_lengths[i]-2*radius)/bounds[1])
        high=(nominal_lengths[i]+2*radius)/bounds[0]
        candidates=[c for c in observation.get('candidates',[]) if low <= c['delay_s'] <= high]
        if observation.get('status')!='ok' or len(candidates)!=1:
            failures.append({'capture_id':cid,'code':'reference_path_unidentified','eligible_candidates':len(candidates)})
        else: selected.append(candidates[0])
    out={'schema_version':'1.0','status':'rejected','physical_validation':False,
         'reference_geometry':'independently supplied calibration only; never inferred room structure',
         'input_result_id':result.get('result_id'),'provenance':result.get('provenance',{}),
         'training_capture_ids':train,'validation_capture_ids':held,'diagnostics':failures,
         'clock_interpretation':'Only c/kappa is estimated. Physical sound speed and absolute source clock rate are not separately identifiable.',
         'conditional_on':['stationary effective point source','correct isolated reference reflection','surveyed poses and reference plane','affine within-recording clocks','no path-dependent unmodeled delay']}
    if failures:return out
    hashes=[observations[cid].get('recording_sha256') for cid in train+held]
    if None in hashes or len(set(hashes)) != len(hashes):
        out['diagnostics'].append({'code':'reference_recordings_reused','message':'Independent calibration and validation recordings require distinct preserved raw bytes.'})
        return out
    waveforms=[observations[cid].get('waveform_sha256') for cid in train+held]
    if any(waveforms) and (None in waveforms or len(set(waveforms))!=len(waveforms)):
        out['diagnostics'].append({'code':'reference_waveforms_reused','message':'Repackaging identical decoded audio cannot supply independent calibration or held-out evidence.'})
        return out
    delay=np.asarray([c['delay_s'] for c in selected])
    timing_variance=[]
    for cid,candidate in zip(train+held,selected):
        observation=observations[cid];clock=observation.get('clock',{})
        relative_rate_std=clock.get('alpha_std',0.)/clock.get('alpha',1.)
        # One selected path per capture: direct-reference and clock terms are
        # diagonal here. They are separate from candidate-local scatter.
        timing_variance.append(candidate['delay_std_s']**2+observation.get('direct_std_s',1e-5)**2
                               +(candidate['delay_s']*relative_rate_std)**2)
    sigma=np.sqrt(timing_variance)
    pose_std=np.asarray([captures[c].get('receiver_position_std_m',.01) for c in train+held])
    axis=np.eye(3)[np.argmin(np.abs(normal))];u=np.cross(normal,axis);u/=np.linalg.norm(u);w=np.cross(normal,u)
    def predict(theta, ref=np.zeros(3)):
        s=theta[:3];v=np.exp(theta[3]);n=normal+ref[1]*u+ref[2]*w;n/=np.linalg.norm(n)
        q=s+2*(offset+ref[0]-n@s)*n
        return (np.linalg.norm(points-q,axis=1)-np.linalg.norm(points-s,axis=1))/v
    def noise(theta):
        s=theta[:3];v=np.exp(theta[3]);q=s+2*(offset-normal@s)*normal
        a=points-q;b=points-s
        grad=(a/np.linalg.norm(a,axis=1)[:,None]-b/np.linalg.norm(b,axis=1)[:,None])/v
        return np.sqrt(sigma*sigma+np.sum(grad*grad,axis=1)*pose_std*pose_std)
    v0=session.get('effective_speed_m_s',session['sound_speed_m_s']/session['source_clock_scale'])
    initial=np.r_[source,np.log(np.clip(v0,bounds[0]+1e-6,bounds[1]-1e-6))]
    lo=np.r_[source-radius,np.log(bounds[0])];hi=np.r_[source+radius,np.log(bounds[1])]
    count=len(train)
    fit=least_squares(lambda t:(predict(t)[:count]-delay[:count])/noise(t)[:count],initial,bounds=(lo,hi),max_nfev=300,xtol=1e-11,ftol=1e-11,gtol=1e-11)
    theta=fit.x;sd=noise(theta);J=_jacobian(predict,theta);A=J[:count]/sd[:count,None]
    singular=np.linalg.svd(A,compute_uv=False)
    out['information_singular_values']=singular.tolist()
    if not fit.success or singular[-1] < singular[0]*1e-4 or np.linalg.norm(theta[:3]-source)>=.98*radius or min(theta-lo)<1e-6 or min(hi-theta)<1e-6:
        out['diagnostics'].append({'code':'calibration_unobservable_or_bound','message':'Change reference geometry/poses or investigate source model; do not apply this fit.'});return out
    residual=predict(theta)-delay;z=residual/sd
    inflation=max(1.,float(np.sum(z[:count]**2)/(count-4)))
    covariance_noise=np.linalg.inv(A.T@A)*inflation
    Jr=_jacobian(lambda ref:predict(theta,ref),np.zeros(3))
    reference_cov=np.diag([offset_std**2,angle_std**2,angle_std**2])
    sensitivity=-np.linalg.pinv(A)@(Jr[:count]/sd[:count,None])
    covariance=covariance_noise+sensitivity@reference_cov@sensitivity.T
    validation_ref=Jr[count:]+J[count:]@sensitivity
    validation_variance=sd[count:]**2+np.einsum('ij,jk,ik->i',J[count:],covariance_noise,J[count:])+np.einsum('ij,jk,ik->i',validation_ref,reference_cov,validation_ref)
    validation_z=residual[count:]/np.sqrt(validation_variance)
    out.update(training_normalized_rms=float(np.sqrt(np.mean(z[:count]**2))),
        validation_normalized_rms=float(np.sqrt(np.mean(validation_z**2))),validation_max_abs_z=float(max(abs(validation_z))),
        validation_nominal_rms_s=float(np.sqrt(np.mean((predict(initial)[count:]-delay[count:])**2))),
        validation_fitted_rms_s=float(np.sqrt(np.mean(residual[count:]**2))),
        evidence=[{'capture_id':cid,'candidate_id':c['candidate_id'],'observed_delay_s':float(delay[i]),'predicted_delay_s':float(predict(theta)[i]),'residual_s':float(residual[i]),'partition':'training' if i<count else 'validation'} for i,(cid,c) in enumerate(zip(train+held,selected))])
    out['acceptance']={'maximum_normalized_rms':2.5,'maximum_validation_abs_z':3.5,'maximum_validation_rms_s':.0001,'maximum_validation_abs_residual_s':.0002}
    out['validation_max_abs_residual_s']=float(max(abs(residual[count:])))
    if out['validation_fitted_rms_s']>.0001 or out['validation_max_abs_residual_s']>.0002 or out['training_normalized_rms']>2.5 or out['validation_normalized_rms']>2.5 or out['validation_max_abs_z']>3.5:
        out['diagnostics'].append({'code':'reference_model_failed_validation','message':'Residuals exceed declared model/survey uncertainty. Preserve raw data and change source route, band or reference geometry.'});return out
    transform=np.diag([1.,1.,1.,np.exp(theta[3])]);joint=transform@covariance@transform
    out.update(status='calibration_proposal',calibration={'source_position_m':theta[:3].tolist(),'effective_speed_m_s':float(np.exp(theta[3])),
        'source_effective_speed_covariance':joint.tolist()},uncertainty='Linearized conditional covariance, including independent receiver/delay noise and shared supplied reference-plane survey uncertainty; not validated coverage under wrong models.')
    encoded=json.dumps({'input':out['input_result_id'],'reference':reference,'calibration':out['calibration']},sort_keys=True,allow_nan=False)
    out['calibration_id']='calibration-'+hashlib.sha256(encoded.encode()).hexdigest()[:20]
    return out
