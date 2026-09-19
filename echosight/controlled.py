"""Four-epoch recording controls for repeatable acoustic change, not causality."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import math
import numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.optimize import linear_sum_assignment
from scipy.signal import hilbert

EPOCHS=('A_before','B_first','B_repeat','A_return')


def _empty(protocol,status='inconclusive',code=None,message=None):
    return {'schema_version':'1.0','protocol_id':protocol.get('protocol_id'), 'status':status,
        'receiver_evidence':[],'conditional_spatial_changes':[], 'epoch_results':[],
        'physical_scene_change_established':False,'physical_validation':False,
        'causal_attribution':'Not established; supplied protocol controls and first-order geometry remain conditional.',
        'absence_semantics':'Missing echoes do not establish removed objects or empty space.',
        'control_provenance':'Operator-declared controls, not independently instrumented verification.',
        'diagnostics':[] if code is None else [{'code':code,'message':message}]}


def _text(value,name):
    if not isinstance(value,str) or not 1<=len(value)<=1024:raise ValueError(name+' must be a nonempty bounded string')


def _load(protocol):
    from .storage import load_session,validate_session
    base=Path.cwd()
    if isinstance(protocol,(str,Path)):
        path=Path(protocol)
        if path.stat().st_size>1024*1024:raise ValueError('protocol exceeds1MiB')
        protocol=json.loads(path.read_text());base=path.parent
    if not isinstance(protocol,dict):raise ValueError('protocol must be an object')
    if protocol.get('schema_version')!='1.0':raise ValueError('unsupported controlled protocol schema')
    for key in ['protocol_id','coordinate_frame_id','intervention_description']:_text(protocol.get(key),key)
    controls=protocol.get('controls')
    if not isinstance(controls,dict):raise ValueError('explicit controls required')
    for key in ['devices_and_source_stationary','only_declared_intervention','restoration_attempted']:
        if controls.get(key) is not True:raise ValueError('control declaration required: '+key)
    std=controls.get('differential_timing_std_s')
    if isinstance(std,bool) or not isinstance(std,(int,float)) or not math.isfinite(std) or not 0<=std<=.01:
        raise ValueError('explicit finite differential_timing_std_s in[0,.01] required')
    epochs=protocol.get('epochs')
    if not isinstance(epochs,list) or len(epochs)!=4 or any(not isinstance(x,dict) for x in epochs):raise ValueError('exactly four epoch objects required')
    if tuple(e.get('epoch') for e in epochs)!=EPOCHS:raise ValueError('epoch order must be A_before,B_first,B_repeat,A_return')
    sessions=[];identities=[]
    for epoch in epochs:
        for key in ['calibration_id','source_configuration_id']:_text(epoch.get(key),key)
        route_ids=epoch.get('route_ids')
        if not isinstance(route_ids,dict):raise ValueError('route_ids required for every epoch')
        value=epoch.get('session')
        if isinstance(value,(str,Path)):
            path=Path(value);session=load_session(path if path.is_absolute() else base/path)
        elif isinstance(value,dict):
            session=validate_session(value)
            for capture in session['captures']:
                if isinstance(capture.get('recording_path'),str):
                    recording=Path(capture['recording_path'])
                    if not recording.is_absolute():capture['recording_path']=str((base/recording).resolve())
        else:raise ValueError('each epoch requires a recording session')
        if session.get('coordinate_frame_id')!=protocol['coordinate_frame_id']:raise ValueError('coordinate frame changed or missing')
        if not session.get('source_position_m') or not session.get('probe'):raise ValueError('source pose and probe required')
        if len(session['captures'])<3:raise ValueError('at least three capture positions required per epoch')
        captures=[]
        for capture in session['captures']:
            for key in ['device_id','receiver_pose_group_id']:_text(capture.get(key),key)
            device=capture['device_id'];_text(route_ids.get(device),'recording route')
            if capture.get('receiver_position_m') is None:raise ValueError('receiver pose required')
            captures.append({k:capture.get(k) for k in ['capture_id','device_id','receiver_pose_group_id','receiver_position_m','receiver_position_std_m']})
        if len({c['device_id'] for c in captures})!=len(captures) or len({c['receiver_pose_group_id'] for c in captures})!=len(captures):
            raise ValueError('stationary protocol requires one capture per distinct device and receiver pose in each epoch')
        if len({tuple(c['receiver_position_m']) for c in captures})!=len(captures):
            raise ValueError('coincident receiver positions cannot count as independent controlled views')
        calibration={k:session.get(k) for k in ['source_position_m','source_position_std_m','sound_speed_m_s','sound_speed_std_m_s',
            'source_clock_scale','source_clock_std_ppm','effective_speed_m_s','source_effective_speed_covariance','probe']}
        identities.append({'calibration':calibration,'captures':sorted(captures,key=lambda x:x['capture_id']),
            'calibration_id':epoch['calibration_id'],'source_configuration_id':epoch['source_configuration_id'],
            'routes':{c['device_id']:route_ids[c['device_id']] for c in session['captures']}})
        sessions.append(session)
    if any(identity!=identities[0] for identity in identities[1:]):raise ValueError('route, source configuration, pose, probe or calibration changed')
    return protocol,sessions


def _rate_std(observation):
    clock=observation.get('clock',{})
    return float(clock.get('alpha_std',0.))/float(clock.get('alpha',1.))


def _persistent(a,b,shared_std):
    left=a.get('candidates',[]);right=b.get('candidates',[])
    if not left or not right:return []
    cost=np.full((len(left),len(right)),1e6);budgets={}
    direct=float(a.get('direct_std_s',0))**2+float(b.get('direct_std_s',0))**2
    for i,x in enumerate(left):
        for j,y in enumerate(right):
            std=math.sqrt(x['delay_std_s']**2+y['delay_std_s']**2+direct+shared_std**2+(x['delay_s']*_rate_std(a))**2+(y['delay_s']*_rate_std(b))**2)
            delta=abs(x['delay_s']-y['delay_s']);budgets[i,j]=std
            if delta<=max(3*std,40e-6):cost[i,j]=delta/max(std,1e-9)
    rows,cols=linear_sum_assignment(cost);out=[]
    for i,j in zip(rows,cols):
        if cost[i,j]>=1e6:continue
        x,y=left[i],right[j]
        out.append({'delay_s':float((x['delay_s']+y['delay_s'])/2),
            # Do not average down common uncertainty or observed repeat disagreement.
            'std_s':float(max(math.hypot(x['delay_std_s'],x['delay_s']*_rate_std(a)),math.hypot(y['delay_std_s'],y['delay_s']*_rate_std(b)),abs(x['delay_s']-y['delay_s'])/math.sqrt(2))),
            'candidate_ids':[x['candidate_id'],y['candidate_id']]})
    return out


def _shifted_features(observations,shared_std):
    a=_persistent(observations[0],observations[3],shared_std);b=_persistent(observations[1],observations[2],shared_std)
    if not a or not b:return []
    costs=np.array([[abs(x['delay_s']-y['delay_s']) for y in b] for x in a]);rows,cols=linear_sum_assignment(costs)
    direct=sum(float(o.get('direct_std_s',0))**2 for o in observations)
    shifts=[]
    for i,j in zip(rows,cols):
        delta=b[j]['delay_s']-a[i]['delay_s']
        std=math.sqrt(a[i]['std_s']**2+b[j]['std_s']**2+direct+shared_std**2)
        if 3*std<abs(delta)<=.006:
            shifts.append({'A_delay_s':a[i]['delay_s'],'B_delay_s':b[j]['delay_s'],'delay_change_s':float(delta),
                'differential_std_bound_s':std,'A_candidate_ids':a[i]['candidate_ids'],'B_candidate_ids':b[j]['candidate_ids'],
                'interpretation':'Persistent observed paths shifted; cross-state identity remains a conditional nearest-delay association.'})
    return shifts


def _receiver_evidence(observations,shared_std):
    rate=min(float(o['response']['sample_rate_hz']) for o in observations)
    end=min(o['response']['start_delay_s']+(len(o['response']['values'])-1)/o['response']['sample_rate_hz'] for o in observations)
    grid=np.arange(.001,min(.07,end),1/rate)
    if len(grid)<100:raise ValueError('insufficient common response window')
    timing=math.sqrt(shared_std**2+sum(float(o.get('direct_std_s',0))**2+(grid[-1]*_rate_std(o))**2 for o in observations))
    vectors=[]
    for observation in observations:
        response=observation['response'];values=np.asarray(response['values'],float)
        envelope=gaussian_filter1d(np.abs(hilbert(values)),max(.5,max(50e-6,3*timing)*response['sample_rate_hz']))
        times=response['start_delay_s']+np.arange(len(values))/response['sample_rate_hz']
        gain=float(observation['quality']['direct_response_amplitude'])
        vectors.append(np.interp(grid,times,envelope)/max(gain,1e-12))
    a1,b1,b2,a2=vectors;scale=max(np.linalg.norm((a1+a2+b1+b2)/4),1e-9)
    repeat_a=float(np.linalg.norm(a1-a2)/scale);repeat_b=float(np.linalg.norm(b1-b2)/scale)
    change=float(np.linalg.norm((b1+b2-a1-a2)/2)/scale)
    derivative=max(float(np.linalg.norm(np.gradient(v,1/rate)))/scale for v in vectors)
    timing_bound=timing*derivative
    repeat_limit=max(.15,3*timing_bound)
    repeat_ok=repeat_a<=repeat_limit and repeat_b<=repeat_limit
    threshold=max(.12,4*max(repeat_a,repeat_b),3*timing_bound)
    return {'capture_id':observations[0]['capture_id'],'A_return_relative_difference':repeat_a,
        'B_repeat_relative_difference':repeat_b,'cross_state_relative_difference':change,
        'timing_relative_difference_bound':timing_bound,'change_gate':threshold,
        'repeat_consistent':bool(repeat_ok),'repeatable_change':bool(repeat_ok and change>threshold),
        'shifted_positive_echoes':_shifted_features(observations,shared_std),
        'gate_semantics':'Engineering consistency bounds, not calibrated p-values; common uncertainty is not divided by capture count.'}


def _spatial_changes(results,receiver_evidence):
    from .evolution import compare_results
    if any(r['status'] not in ('ok','partial') or not r.get('surfaces') for r in results):return []
    comparisons=[compare_results(results[0],results[3]),compare_results(results[1],results[2]),compare_results(results[0],results[1])]
    if any(c['status']!='comparable' for c in comparisons):return []
    returned={c['previous_surface_id']:c for c in comparisons[0]['correspondences']}
    repeated={c['previous_surface_id']:c for c in comparisons[1]['correspondences']}
    surfaces=[{p['surface_id']:p for p in r['surfaces']} for r in results]
    positive={e['capture_id']:e['shifted_positive_echoes'] for e in receiver_evidence if e['repeatable_change'] and e['shifted_positive_echoes']}
    changes=[]
    for pair in comparisons[2]['correspondences']:
        aid=pair['previous_surface_id'];bid=pair['current_surface_id']
        if aid not in returned or bid not in repeated:continue
        planes=[surfaces[0][aid],surfaces[1][bid],surfaces[2][repeated[bid]['current_surface_id']],surfaces[3][returned[aid]['current_surface_id']]]
        if any(not p.get('uncertainty') or p['uncertainty'].get('image_source_covariance_m2') is None for p in planes):continue
        # At the shared source, |d-n.s|=|q-s|/2. Propagate that invariant
        # quantity, bounding unknown q/source and inter-epoch correlations by
        # sums of standard deviations rather than assuming independence.
        stds=[]
        for plane,result in zip(planes,results):
            normal=np.asarray(plane['normal']);qcov=np.asarray(plane['uncertainty']['image_source_covariance_m2'])
            acquisition=result['acquisition'];joint=acquisition.get('source_effective_speed_covariance')
            scov=np.asarray(joint)[:3,:3] if joint is not None else np.eye(3)*acquisition.get('source_position_std_m',.01)**2
            stds.append(.5*(math.sqrt(max(0,float(normal@qcov@normal)))+math.sqrt(max(0,float(normal@scov@normal)))))
        bound=float(sum(stds));within=max(abs(returned[aid]['offset_change_m']),abs(repeated[bid]['offset_change_m']))
        supports=[{e['capture_id']:e['candidate_id'] for e in p.get('support',[])} for p in planes]
        supporting=set.intersection(*[set(e) for e in supports])&set(positive)
        supporting={cid for cid in supporting if any(
            shift['A_candidate_ids']==[supports[0][cid],supports[3][cid]] and
            shift['B_candidate_ids']==[supports[1][cid],supports[2][cid]] for shift in positive[cid])}
        if len(supporting)<3 or abs(pair['offset_change_m'])<=max(3*bound,4*within,.01):continue
        if returned[aid]['normal_change_deg']>3 or repeated[bid]['normal_change_deg']>3:continue
        changes.append({**pair,'A_return_surface_id':returned[aid]['current_surface_id'],
            'B_repeat_surface_id':repeated[bid]['current_surface_id'],'conservative_offset_std_bound_m':bound,
            'positive_echo_capture_ids':sorted(supporting),'claim':'Conditional displacement of supported planar reflection geometry, not object identity or causal proof.'})
    return changes


def _compact_epoch(result):
    """Keep geometry/path evidence; dense responses are reproducible from raw inputs."""
    result=dict(result);observations=[]
    for observation in result.get('observations',[]):
        observation=dict(observation)
        if isinstance(observation.get('response'),dict):
            response=dict(observation['response'])
            values=response.pop('values',None)
            if values is not None:response.update(values_omitted=True,sample_count=len(values),samples_available_by_reprocessing_raw=True)
            observation['response']=response
        observations.append(observation)
    result['observations']=observations
    return result


def _native_control_conflicts(protocol,observations,ids):
    """Known raw-manifest contradictions cannot be overridden by outer labels.

    Manifests remain unauthenticated declarations. Legacy WAV controls still
    rely on operator declarations; absence is never promoted to observed proof.
    """
    from .acquisition import source_declaration_consistency
    conflicts=[]
    source_consistency=source_declaration_consistency(epoch[cid].get('acquisition_evidence') for epoch in observations for cid in sorted(ids))
    for cid in sorted(ids):
        evidence=[epoch[cid].get('acquisition_evidence') for epoch in observations]
        if not any(e is not None for e in evidence):continue
        if any(e is None for e in evidence):
            conflicts.append(cid+': native acquisition evidence missing in some epochs');continue
        signatures=[]
        for index,e in enumerate(evidence):
            # The pipeline derives these from the immutable raw package.
            signatures.append({key:e[key] for key in ('device','recorder','route_initial','route_final')})
            signatures[-1]['session']={key:e['session'][key] for key in ('category','mode','activated_sample_rate_hz')}
            declaration=e['source_declaration']
            native=declaration['configuration_id'];outer=protocol['epochs'][index]['source_configuration_id']
            if native.strip().lower()!='unknown' and outer.strip().lower()!='unknown' and native!=outer:
                conflicts.append(cid+': native source configuration contradicts epoch '+EPOCHS[index])
        if any(signature!=signatures[0] for signature in signatures[1:]):
            conflicts.append(cid+': observed recorder, device, input route or active format changed across epochs')
    for key in source_consistency['conflicting_fields']:
        conflicts.append('native source '+key+' differs across captures/epochs')
    return conflicts


def _finalize_controlled(out,cancel):
    """Publish no cross-epoch decision when cooperative cancellation is observed."""
    if out['status']!='cancelled' and not cancel():return out
    out=dict(out)
    out.update(status='cancelled',receiver_evidence=[],conditional_spatial_changes=[],
               physical_scene_change_established=False)
    out['diagnostics']=list(out['diagnostics'])
    if not any(d.get('code')=='cancelled_by_caller' for d in out['diagnostics']):
        out['diagnostics'].append({'code':'cancelled_by_caller','message':'Cross-epoch comparison was cancelled. Retained epoch results and recording hashes are input evidence for recovery, not a completed change decision.'})
    return out


def process_controlled_protocol(protocol,cancel=None,progress=None):
    """Raw-recording entry point; exactly four epochs, bounded by session limits."""
    from .pipeline import process_session
    cancel=cancel or (lambda:False);progress=progress or (lambda fraction,message='':None)
    if cancel():return _finalize_controlled(_empty(protocol if isinstance(protocol,dict) else {},'cancelled'),cancel)
    try:protocol,sessions=_load(protocol)
    except (ValueError,TypeError,KeyError,OSError) as exc:return _finalize_controlled(_empty(protocol if isinstance(protocol,dict) else {},code='protocol_invalid_or_controls_changed',message=str(exc)),cancel)
    out=_empty(protocol);out['declared_controls']=protocol['controls'];out['intervention_description']=protocol['intervention_description']
    out['coordinate_frame_id']=protocol['coordinate_frame_id']
    out['epoch_control_declarations']=[{k:e[k] for k in ('epoch','calibration_id','source_configuration_id','route_ids')} for e in protocol['epochs']]
    try:out['protocol_sha256']=hashlib.sha256(json.dumps(protocol,sort_keys=True,allow_nan=False).encode()).hexdigest()
    except (ValueError,TypeError) as exc:return _finalize_controlled(_empty(protocol,code='protocol_invalid_or_controls_changed',message=str(exc)),cancel)
    results=[]
    for i,session in enumerate(sessions):
        if cancel():out['status']='cancelled';return _finalize_controlled(out,cancel)
        result=process_session(session,cancel=cancel,progress=lambda f,m='',i=i:progress((i+f)/4,m))
        results.append(result);out['epoch_results'].append({'epoch':EPOCHS[i],'result':_compact_epoch(result)})
        if result['status']=='cancelled':out['status']='cancelled';return _finalize_controlled(out,cancel)
    observations=[{o['capture_id']:o for o in r.get('observations',[])} for r in results]
    ids={c['capture_id'] for c in sessions[0]['captures']}
    if any(set(o)!=ids or any(v.get('status')!='ok' for v in o.values()) for o in observations):
        out['diagnostics'].append({'code':'capture_quality_failed','message':'Every declared capture must pass signal checks in all four epochs.'});return _finalize_controlled(out,cancel)
    conflicts=_native_control_conflicts(protocol,observations,ids)
    if conflicts:
        out['diagnostics'].append({'code':'native_controls_contradict_protocol','message':'; '.join(conflicts)})
        return _finalize_controlled(out,cancel)
    hashes=[o.get('recording_sha256') for epoch in observations for o in epoch.values()]
    if None in hashes or len(set(hashes))!=len(hashes):
        out['diagnostics'].append({'code':'recordings_reused','message':'Independent epochs and devices require distinct preserved recording bytes.'});return _finalize_controlled(out,cancel)
    waveforms=[o.get('waveform_sha256') for epoch in observations for o in epoch.values()]
    if any(waveforms) and (None in waveforms or len(set(waveforms))!=len(waveforms)):
        out['diagnostics'].append({'code':'recording_waveforms_reused','message':'Distinct containers cannot make identical decoded audio independent across epochs or devices.'})
        return _finalize_controlled(out,cancel)
    try:
        for cid in sorted(ids):
            if cancel():out['status']='cancelled';return _finalize_controlled(out,cancel)
            out['receiver_evidence'].append(_receiver_evidence([o[cid] for o in observations],protocol['controls']['differential_timing_std_s']))
    except (KeyError,ValueError,TypeError) as exc:
        out['diagnostics'].append({'code':'response_comparison_unavailable','message':str(exc)});return _finalize_controlled(out,cancel)
    if any(not e['repeat_consistent'] for e in out['receiver_evidence']):
        out['diagnostics'].append({'code':'return_or_repeat_failed','message':'A-return or B-repeat differs beyond the declared timing and repeatability gates.'});return _finalize_controlled(out,cancel)
    changed=sum(e['repeatable_change'] for e in out['receiver_evidence'])
    if changed<max(3,math.ceil(len(ids)/2)):
        out['status']='no_repeatable_change'
        out['diagnostics'].append({'code':'change_not_established','message':'Insufficient repeated multi-view change. This does not prove scene identity.'});return _finalize_controlled(out,cancel)
    out['status']='repeatable_acoustic_change_unlocalized'
    out['conditional_spatial_changes']=_spatial_changes(results,out['receiver_evidence'])
    if out['conditional_spatial_changes']:out['status']='conditional_spatial_change'
    if cancel():out['status']='cancelled';return _finalize_controlled(out,cancel)
    out['diagnostics'].append({'code':'controlled_acoustic_difference','message':'Repeated normalized acoustic responses differ between declared states; localization and attribution remain conditional.'})
    return _finalize_controlled(out,cancel)
