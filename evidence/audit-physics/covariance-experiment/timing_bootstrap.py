"""Experimental whole-repetition bootstrap of the complete excess-delay estimator.

No Hessian IID-noise assumption. Copies include pulse/echo waveform correlation;
clock, direct reference and empirical kernel are re-estimated in every draw.
"""
import numpy as np
from scipy.optimize import linear_sum_assignment


def estimate(samples, sample_rate_hz, probe, observation, processor, draws=31, seed=9274, cancel=None):
    if not isinstance(draws,int) or isinstance(draws,bool) or not 15<=draws<=63:
        raise ValueError('bootstrap draws must be from 15 to 63')
    if observation.get('estimator')!='joint_kernel' or observation.get('status')!='ok':
        raise ValueError('joint-kernel accepted observation required')
    candidates=observation['candidates'];ids=[c['candidate_id'] for c in candidates]
    if not ids:return dict(status='no_candidates',candidate_ids=[],covariance_s2=[])
    fs=float(sample_rate_hz);y=np.asarray(samples,float);source_fs=probe['sample_rate_hz']
    alpha=observation['clock']['alpha'];intercept=observation['clock']['intercept_s']
    starts=np.asarray(probe['pilot_start_samples'],float)/source_fs
    margin=.004;anchors=(alpha*(starts-margin)+intercept)*fs
    bases=np.floor(anchors).astype(int)
    count=int(np.ceil(alpha*(probe['duration_s']+probe['max_echo_delay_s']+2*margin)*fs))
    if min(bases)<0 or max(bases)+count>len(y):raise ValueError('bootstrap block outside recording')
    if len(starts)>16 or count>fs*.32 or len(y)>fs*30:raise ValueError('bootstrap allocation bound')
    expected=np.asarray([c['delay_s'] for c in candidates]);rng=np.random.default_rng(seed)
    floor=max(.5/source_fs,.5/(probe['high_hz']-probe['low_hz']))
    # Frozen association gate; closer paths have smaller disjoint neighborhoods.
    radius=np.full(len(ids),4*floor)
    if len(ids)>1:
        distances=abs(expected[:,None]-expected[None,:]);np.fill_diagonal(distances,np.inf)
        radius=np.minimum(radius,.49*distances.min(axis=1))
    indices=np.arange(len(y),dtype=float);local=np.arange(count,dtype=float)
    estimates=[];rates=[];invalid=[]
    for draw in range(draws):
        if cancel and cancel():return dict(status='cancelled',candidate_ids=ids)
        replay=y.copy();selection=rng.integers(0,len(starts),len(starts))
        for destination,selected in enumerate(selection):
            # Transfer the whole pulse/echo segment at the fitted source time,
            # retaining the chosen repetition's residual clock/shape variation.
            source_index=anchors[selected]+local-(anchors[destination]-bases[destination])
            replay[bases[destination]:bases[destination]+count]=np.interp(source_index,indices,y)
        out=processor(replay,int(fs),probe,observation['capture_id'],estimator='joint_kernel',cancel=cancel)
        if out['status']!='ok':invalid.append(dict(draw=draw,reason='recording_rejected'));continue
        peaks=out['candidates'];found=np.asarray([c['delay_s'] for c in peaks]);cost=abs(expected[:,None]-found[None,:])
        if len(found)<len(expected):invalid.append(dict(draw=draw,reason='candidate_missing'));continue
        left,right=linear_sum_assignment(cost/radius[:,None])
        if len(left)!=len(expected) or np.any(cost[left,right]>radius[left]):
            invalid.append(dict(draw=draw,reason='candidate_assignment_unstable'));continue
        vector=np.empty(len(expected));vector[left]=found[right]
        estimates.append(vector);rates.append(out['clock']['alpha'])
    metadata=dict(candidate_ids=ids,draws_requested=draws,draws_accepted=len(estimates),invalid_draws=invalid,
        includes_direct_reference=True,includes_empirical_direct_kernel=True,includes_relative_clock=True,
        includes_amplitude_nuisance=True,includes_source_absolute_rate=False,includes_pose=False,
        sampling_unit='entire pulse and echo waveform repetition',coverage_status='development_unqualified',
        limitations=['Seven/small repetition sample limits bootstrap calibration.',
                    'Conditions on stable selected path set; instability is explicitly counted.',
                    'Assumes independent stationary repetitions; common deterministic model bias is unidentifiable.',
                    'Subsample block transfer interpolates waveforms; measured interpolation bias is not physical uncertainty.'])
    if len(estimates)<max(15,int(np.ceil(.9*draws))):return dict(status='unstable',**metadata)
    values=np.asarray(estimates);noise=np.atleast_2d(np.cov(values,rowvar=False,ddof=1));noise=(noise+noise.T)/2
    # Retain the old explicit resolution/model floors without counting them twice.
    # One independent echo floor plus one shared direct-reference floor.
    model_floor=floor**2*(np.eye(len(ids))+np.ones((len(ids),len(ids))))
    covariance=noise+model_floor
    joint=np.cov(np.column_stack([values,np.asarray(rates)]),rowvar=False,ddof=1)
    return dict(status='estimated',noise_covariance_s2=noise.tolist(),covariance_s2=covariance.tolist(),
        declared_timing_floor_s=floor,model_floor_semantics='heuristic isolated echo and shared direct resolution floors; not calibrated bias probability',
        bootstrap_mean_delay_s=values.mean(axis=0).tolist(),bootstrap_mean_shift_s=(values.mean(axis=0)-expected).tolist(),
        relative_clock_cross_covariance_s=np.asarray(joint[:-1,-1]).tolist(),relative_clock_variance=float(joint[-1,-1]),**metadata)


def validate(observation):
    """Return candidate ID mapping and the complete timing covariance, if supplied."""
    block=observation.get('candidate_delay_covariance')
    if block is None:return None
    ids=block.get('candidate_ids');available=[c['candidate_id'] for c in observation.get('candidates',[])]
    if not isinstance(ids,list) or len(ids)>18 or any(not isinstance(i,str) for i in ids) or len(set(ids))!=len(ids) or set(ids)!=set(available):
        raise ValueError('timing covariance candidate identity mismatch')
    if not all(block.get(k) is True for k in ['includes_direct_reference','includes_relative_clock','includes_empirical_direct_kernel','includes_amplitude_nuisance']):
        raise ValueError('timing covariance component accounting is unsupported')
    C=np.asarray(block.get('covariance_s2'),float)
    scale=max(float(np.max(np.abs(C))) if C.size else 0.,1e-30)
    if C.shape!=(len(ids),len(ids)) or not np.all(np.isfinite(C)) or not np.allclose(C,C.T,atol=scale*1e-10,rtol=1e-10):
        raise ValueError('timing covariance must be finite symmetric and dimensionally consistent')
    if len(ids) and (np.linalg.eigvalsh(C).min() < -scale*1e-10 or np.diag(C).min()<=0):
        raise ValueError('timing covariance must be positive semidefinite with positive diagonal')
    return {cid:i for i,cid in enumerate(ids)},C


def timing_variance(observation,candidate):
    checked=validate(observation)
    if checked is not None:
        ids,C=checked
        return float(C[ids[candidate['candidate_id']],ids[candidate['candidate_id']]])
    clock=observation.get('clock',{})
    return (float(candidate.get('delay_std_s',1e-5))**2
            +float(observation.get('direct_std_s',1e-5))**2
            +(float(candidate['delay_s'])*float(clock.get('alpha_std',0))/float(clock.get('alpha',1)))**2)
