"""Exact three gate functions extracted from the frozen runner; globals supplied by replay.py."""
import sys
import numpy as np

def score(result,truth):
    from scipy.optimize import linear_sum_assignment
    from evaluation.metrics import score_surfaces
    predicted=result.get('surfaces',[]);expected=truth['surfaces'];c=cfg()['acceptance'];matches=[]
    errors=np.zeros((len(predicted),len(expected),2))
    for i,p in enumerate(predicted):
        n=np.array(p['normal']);n=n/np.linalg.norm(n)
        for j,t in enumerate(expected):
            errors[i,j]=[np.degrees(np.arccos(np.clip(abs(n@t['normal']),0,1))),abs(n@t['anchor_m']-p['offset_m'])]
    if predicted and expected:
        valid=(errors[:,:,0]<=c['normal_error_deg'])&(errors[:,:,1]<=c['anchor_error_m'])
        cost=(~valid)*(max(len(predicted),len(expected))+1)+np.minimum(errors[:,:,0]/c['normal_error_deg']+errors[:,:,1]/c['anchor_error_m'],2)/2
        ii,jj=linear_sum_assignment(cost)
        for i,j in zip(ii,jj):
            if valid[i,j]: matches.append(dict(predicted_id=predicted[i]['surface_id'],truth_id=expected[j]['surface_id'],
                normal_error_deg=float(errors[i,j,0]),anchor_error_m=float(errors[i,j,1]),horizontal=abs(expected[j]['normal'][2])>=.9))
    return dict(matched=len(matches),unmatched=len(predicted)-len(matches),missed=len(expected)-len(matches),
        horizontal=sum(m['horizontal'] for m in matches),matches=matches,
        six_plane_mean_anchor_error_m=float(np.mean([m['anchor_error_m'] for m in matches])) if len(matches)==6 else None,
        historical_offset_015m=score_surfaces(result,truth))

def withheld_metrics(fit):
    result=fit['result'];held=fit['withheld_extraction'];c=cfg()['acceptance'];rows=[]
    session=result['acquisition'];s=np.array(session['source_position_m']);v=session.get('effective_speed_m_s',session['sound_speed_m_s']/session['source_clock_scale'])
    for surface in result.get('surfaces',[]):
        n=np.array(surface['normal']);d=surface['offset_m'];q=s+2*(d-n@s)*n
        for o in held['observations']:
            r=np.array(o['receiver_position_m']);prediction=float((np.linalg.norm(r-q)-np.linalg.norm(r-s))/v)
            candidates=[p for p in o.get('candidates',[]) if not p.get('merged',False) and abs(p['delay_s']-prediction)<=c['withheld_candidate_window_s']]
            row=dict(surface_id=surface['surface_id'],capture_id=o['capture_id'],predicted_delay_s=prediction,
                observation_status=o['status'],candidate_count=len(candidates),status='missing_or_ambiguous')
            if o['status']=='ok' and len(candidates)==1:
                row.update(status='unique',candidate_id=candidates[0]['candidate_id'],residual_s=float(candidates[0]['delay_s']-prediction))
            rows.append(row)
    # One observed peak cannot validate two distinct predicted paths.
    selected={}
    for row in rows:
        if row['status']=='unique':selected.setdefault((row['capture_id'],row['candidate_id']),[]).append(row)
    for values in selected.values():
        if len(values)>1:
            for row in values:row['status']='candidate_reused_by_multiple_surfaces'
    good=[r['residual_s'] for r in rows if r['status']=='unique']
    complete=len(rows)==24 and len(good)==24
    rms=float(np.sqrt(np.mean(np.square(good)))) if good else None
    maximum=float(max(abs(x) for x in good)) if good else None
    groups=[]
    for surface in result.get('surfaces',[]):
        sub=[r for r in rows if r['surface_id']==surface['surface_id']];values=[r['residual_s'] for r in sub if r['status']=='unique']
        groups.append(dict(surface_id=surface['surface_id'],expected=4,unique=len(values),rms_s=float(np.sqrt(np.mean(np.square(values)))) if values else None))
    return dict(rows=rows,per_surface=groups,expected=24,unique=len(good),complete=complete,rms_s=rms,max_abs_s=maximum,
                passed=bool(complete and rms<=c['withheld_rms_s'] and maximum<=c['withheld_max_s']))

def summarize():
    rows=[];c=cfg();sys.path.insert(0,str(ROOT))
    # All fits must exist before any evaluation truth is loaded.
    paths=[P/'fits'/f'{family}-{seed}-{method}.json' for seed in c['seeds'] for family in ('room','direct_only') for method in c['methods']]
    assert all(p.is_file() for p in paths)
    fits=[read(p) for p in paths]
    for fit in fits:
        truth=read(P/'raw'/f"{fit['family']}-{fit['seed']}"/'truth.json');m=score(fit['result'],truth)
        held=withheld_metrics(fit) if fit['family']=='room' else None
        admission_pass=len(fit['result']['observations'])==12 and all(o['status']=='ok' for o in fit['result']['observations'])
        passed=(m['matched']==6 and m['horizontal']==2 and m['unmatched']==0 and held['passed']) if held else not fit['result']['surfaces']
        rows.append(dict(seed=fit['seed'],family=fit['family'],method=fit['method'],status=fit['result']['status'],geometry=m,withheld=held,
            raw_processing_s=fit['raw_processing_s'],runtime_pass=fit['raw_processing_s']<=c['acceptance']['raw_processing_s'],
            geometry_and_prediction_pass=bool(passed and admission_pass),all_mapping_recordings_accepted=admission_pass,runtime_scope=fit['runtime_scope'],observation_hash=fit['observation_hash'],
            admission=[dict(capture_id=o['capture_id'],status=o['status'],candidate_count=len(o.get('candidates',[])),diagnostics=o.get('diagnostics',[])) for o in fit['result']['observations']]))
    benefits=[]
    for seed in c['seeds']:
        cases={r['method']:r for r in rows if r['seed']==seed and r['family']=='room'};j=cases['joint_mapper']
        comparisons=[]
        for comparator in ('nominal_mapper','one_x_mapper'):
            b=cases[comparator];gj,gb=j['geometry'],b['geometry'];hj,hb=j['withheld'],b['withheld']
            # No favorable subset. Incomplete comparator counts as recovery gain,
            # but never invents its missing residual/geometry error.
            comparable=hj['complete'] and hb['complete'] and gj['matched']==gb['matched']==6
            recovery_gain=gj['matched']==6 and gb['matched']<6
            lower_rms=comparable and hb['rms_s']-hj['rms_s']>=c['acceptance']['minimum_withheld_rms_gain_s']
            lower_anchor=comparable and gb['six_plane_mean_anchor_error_m']-gj['six_plane_mean_anchor_error_m']>=c['acceptance']['minimum_mean_anchor_gain_m']
            no_regression=gj['unmatched']<=gb['unmatched'] and gj['missed']<=gb['missed']
            comparisons.append(dict(comparator=comparator,comparable_complete_error_sets=comparable,recovery_gain=recovery_gain,
                lower_withheld_rms=lower_rms,lower_mean_anchor_error=lower_anchor,no_false_or_missed_regression=no_regression,
                comparator_complete_gate_failed=not b['geometry_and_prediction_pass'],
                gain=bool(j['geometry_and_prediction_pass'] and no_regression and (not b['geometry_and_prediction_pass'] or (lower_rms and lower_anchor)))))
        benefits.append(dict(seed=seed,comparisons=comparisons,benefit=all(x['gain'] for x in comparisons)))
    comparable_hashes=all(len({r['observation_hash'] for r in rows if r['seed']==seed and r['family']==family})==1 for seed in c['seeds'] for family in ('room','direct_only'))
    joint=[r for r in rows if r['method']=='joint_mapper'];recall_gain=sum(r['geometry']['matched'] for r in joint if r['family']=='room')>sum(r['geometry']['matched'] for r in rows if r['method']=='joint_first_echo' and r['family']=='room')
    transfer=all(r['geometry_and_prediction_pass'] and r['runtime_pass'] for r in joint)
    save(P/'results.json',dict(rows=rows,benefits=benefits,identical_observations=comparable_hashes,transfer_pass=transfer,
         first_echo_recall_gain=recall_gain,promotion_criteria_pass=transfer and comparable_hashes and recall_gain and all(b['benefit'] for b in benefits),
         decision_semantics='Development transfer evidence only. A pass requires independent review, not automatic public feature promotion.',limits=c['limits']))
