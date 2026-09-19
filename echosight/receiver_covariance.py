"""Explicit receiver survey covariance, independent of source and speed.

Full matrices replace scalar receiver uncertainties. They are not estimates
learned from echo residuals and do not account for biased survey means.
"""
import numpy as np
from .inference import _check

MAX_GROUPS = 64
MAX_ID_LENGTH = 160


def _group_id(value):
    if not isinstance(value,str) or not 1<=len(value)<=MAX_ID_LENGTH:
        raise ValueError('receiver pose group ID must be a string of 1 to 160 characters')
    return value


def validate(bundle,processed,cancel=None):
    """Check full declaration against ALL supplied poses, not only accepted echoes.

    Raw entry supplies sessions before reading WAVs; prepared entry supplies both
    capture declarations and observations. Neither input is modified.
    """
    _check(cancel)
    shared=bundle.get('shared_calibration',{})
    if 'receiver_pose_covariance' not in shared:return None
    declaration=shared['receiver_pose_covariance']
    if not isinstance(declaration,dict):raise ValueError('receiver_pose_covariance must be an object')
    if set(declaration)!={'group_ids','covariance_m2','assumption','scalar_policy'}:
        raise ValueError('receiver_pose_covariance requires group_ids, covariance_m2, assumption, scalar_policy only')
    if declaration['assumption']!='independent_of_source_and_effective_speed':
        raise ValueError('receiver covariance must declare independence of source and effective speed')
    if declaration['scalar_policy']!='replace':
        raise ValueError('receiver covariance scalar_policy must be replace')
    groups=declaration['group_ids']
    if not isinstance(groups,list) or not 1<=len(groups)<=MAX_GROUPS:
        raise ValueError('receiver covariance group budget requires 1 to 64 IDs')
    for group in groups:_group_id(group)
    if len(set(groups))!=len(groups):raise ValueError('receiver covariance group IDs must be unique')
    size=3*len(groups);value=declaration['covariance_m2']
    # Reject oversized/ragged/string/bool matrices before numeric allocation.
    if not isinstance(value,list) or len(value)!=size or any(not isinstance(row,list) or len(row)!=size for row in value):
        raise ValueError('receiver covariance shape must be 3G by 3G')
    if any(isinstance(x,bool) or not isinstance(x,(int,float)) for row in value for x in row):
        raise ValueError('receiver covariance entries must be JSON numbers')
    try:covariance=np.asarray(value,dtype=float)
    except (OverflowError,TypeError,ValueError) as exc:raise ValueError('receiver covariance entries exceed numeric range') from exc
    if not np.isfinite(covariance).all() or not np.allclose(covariance,covariance.T,rtol=1e-8,atol=1e-12):
        raise ValueError('receiver covariance must be finite and symmetric')
    covariance=covariance/2+covariance.T/2
    _check(cancel)
    if np.linalg.eigvalsh(covariance).min() < -1e-12:raise ValueError('receiver covariance must be positive semidefinite')
    poses={};records=0
    def register(group,position):
        group=_group_id(group)
        if not isinstance(position,(list,tuple,np.ndarray)) or len(position)!=3:
            raise ValueError('receiver covariance requires finite three-dimensional positions')
        try:p=np.asarray(position,dtype=float)
        except (OverflowError,TypeError,ValueError) as exc:raise ValueError('receiver position exceeds numeric range') from exc
        if p.shape!=(3,) or not np.isfinite(p).all():raise ValueError('receiver covariance requires finite three-dimensional positions')
        if group in poses and not np.allclose(poses[group],p,atol=1e-8,rtol=0):
            raise ValueError('reused receiver pose group has inconsistent survey position')
        poses[group]=p
        if len(poses)>MAX_GROUPS:raise ValueError('receiver covariance group budget exceeded')
    for item in processed:
        _check(cancel)
        if not isinstance(item,dict) or not isinstance(item.get('session'),dict):raise ValueError('receiver covariance requires session objects')
        captures=item['session'].get('captures',[]);observations=item.get('observations',[])
        if not isinstance(captures,list) or not isinstance(observations,list):raise ValueError('receiver records must be arrays')
        records+=max(len(captures),len(observations))
        if records>MAX_GROUPS:raise ValueError('joint capture resource limit exceeded')
        by_id={}
        for capture in captures:
            if not isinstance(capture,dict):raise ValueError('receiver capture must be an object')
            group=capture.get('receiver_pose_group_id');register(group,capture.get('receiver_position_m'))
            by_id[capture['capture_id']]=group
        for observation in observations:
            if not isinstance(observation,dict):raise ValueError('receiver observation must be an object')
            capture_group=by_id.get(observation['capture_id'])
            group=observation.get('receiver_pose_group_id',capture_group)
            if capture_group is not None and capture_group!=group:raise ValueError('capture and observation receiver group disagree')
            register(group,observation.get('receiver_position_m'))
    if set(groups)!=set(poses):raise ValueError('receiver covariance group IDs must exactly cover declared receiver poses')
    return dict(index={group:i for i,group in enumerate(groups)},covariance=covariance)


def project(groups,gradients,stds,calibration):
    """Project receiver-position errors into full delay covariance (seconds²)."""
    gradients=np.asarray(gradients);count=len(groups)
    if calibration is None:
        # Historical scalar convention: distinct groups independent, reused
        # groups share one isotropic survey draw across all source sessions.
        return np.array([[float(gradients[i]@gradients[j])*stds[i]**2 if groups[i]==groups[j] else 0.
                          for j in range(count)] for i in range(count)])
    matrix=np.zeros((count,len(calibration['covariance'])))
    for i,group in enumerate(groups):
        start=3*calibration['index'][group];matrix[i,start:start+3]=gradients[i]
    result=matrix@calibration['covariance']@matrix.T
    if not np.isfinite(result).all():raise ValueError('receiver covariance projection exceeds finite numeric range')
    return result


def marginal(groups,gradients,stds,calibration):
    """Marginal variances for the existing conservative per-path parent gate."""
    if calibration is None:return np.einsum('ij,ij->i',gradients,gradients)*np.asarray(stds)**2
    values=[]
    for group,gradient in zip(groups,gradients):
        start=3*calibration['index'][group]
        values.append(gradient@calibration['covariance'][start:start+3,start:start+3]@gradient)
    result=np.asarray(values)
    if not np.isfinite(result).all():raise ValueError('receiver covariance projection exceeds finite numeric range')
    return result


def describe(calibration):
    if calibration is None:
        return dict(mode='scalar_receiver_groups',assumption='independent receiver groups and independent of source/effective speed; reused IDs share one isotropic survey error')
    return dict(mode='full_receiver_pose_covariance',group_ids=list(calibration['index']),
                covariance_m2=calibration['covariance'].tolist(),
                assumption='independent_of_source_and_effective_speed',scalar_policy='replace',
                semantics='Supplied receiver-position covariance in the common metre coordinate frame. Scalar receiver_position_std_m values are retained as provenance but excluded from propagation. No source/receiver cross covariance or survey bias is represented.')
