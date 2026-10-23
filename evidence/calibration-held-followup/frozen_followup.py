"""Exact held_metrics and summarize functions from records/original-run.py; replay supplies globals."""
def held_metrics(fit,out):
    # Exact frozen association code, then make incomplete-set statistics explicit.
    gates=load_module(base()/'frozen_gates.py','frozen_gates');gates.cfg=cfg
    metrics=gates.withheld_metrics(dict(result=fit['result'],withheld_extraction=out))
    metrics['unique_subset_rms_s']=metrics.pop('rms_s');metrics['unique_subset_max_abs_s']=metrics.pop('max_abs_s')
    metrics['complete_rms_s']=metrics['unique_subset_rms_s'] if metrics['complete'] else None
    metrics['complete_max_abs_s']=metrics['unique_subset_max_abs_s'] if metrics['complete'] else None
    return metrics

def summarize(extractions):
    old=read(base()/'expected-results.json');c=cfg();rows=[]
    for seed in c['seeds']:
        for method in c['methods']:
            fit=read(base()/f'fits/room-{seed}-{method}.json');previous=next(r for r in old['rows'] if (r['seed'],r['family'],r['method'])==(seed,'room',method));m=held_metrics(fit,extractions[seed]);g=previous['geometry']
            geometry_ok=g['matched']==6 and g['horizontal']==2 and g['unmatched']==0
            rows.append(dict(seed=seed,method=method,withheld=m,geometry=g,all_mapping_recordings_accepted=previous['all_mapping_recordings_accepted'],geometry_and_prediction_pass=bool(geometry_ok and m['passed'] and previous['all_mapping_recordings_accepted']),runtime_pass=previous['runtime_pass'],raw_processing_s=previous['raw_processing_s'],mapping_runtime_commit=c['historical_runtime_commit'],mapping_timing_freshly_measured=False,observations_sha256=sha(P/'extractions'/f'{seed}.json')))
    benefits=[]
    for seed in c['seeds']:
        cases={r['method']:r for r in rows if r['seed']==seed};j=cases['joint_mapper'];comparisons=[]
        for method in ('nominal_mapper','one_x_mapper'):
            b=cases[method];hj,hb=j['withheld'],b['withheld'];gj,gb=j['geometry'],b['geometry'];comparable=hj['complete'] and hb['complete'] and gj['matched']==gb['matched']==6
            rms_gain=hb['complete_rms_s']-hj['complete_rms_s'] if comparable else None;anchor_gain=gb['six_plane_mean_anchor_error_m']-gj['six_plane_mean_anchor_error_m'] if comparable else None
            no_regression=gj['unmatched']<=gb['unmatched'] and gj['missed']<=gb['missed'];gain=j['geometry_and_prediction_pass'] and no_regression and (not b['geometry_and_prediction_pass'] or (comparable and rms_gain>=c['acceptance']['minimum_withheld_rms_gain_s'] and anchor_gain>=c['acceptance']['minimum_mean_anchor_gain_m']))
            comparisons.append(dict(comparator=method,complete_rms_gain_s=rms_gain,mean_anchor_gain_m=anchor_gain,comparator_complete_gate_failed=not b['geometry_and_prediction_pass'],no_false_or_missed_regression=no_regression,gain=bool(gain)))
        benefits.append(dict(seed=seed,comparisons=comparisons,benefit=all(x['gain'] for x in comparisons)))
    nulls=[r for r in old['rows'] if r['family']=='direct_only'];null_pass=all(r['geometry_and_prediction_pass'] and r['runtime_pass'] for r in nulls if r['method']=='joint_mapper')
    joints=[r for r in rows if r['method']=='joint_mapper'];transfer=all(r['geometry_and_prediction_pass'] and r['runtime_pass'] for r in joints) and null_pass
    recall=sum(r['geometry']['matched'] for r in joints)>sum(r['geometry']['matched'] for r in rows if r['method']=='joint_first_echo')
    return dict(rows=rows,benefits=benefits,retained_nulls=nulls,retained_original_transfer_pass=old['transfer_pass'],retained_original_promotion_pass=old['promotion_criteria_pass'],transfer_pass=transfer,promotion_criteria_pass=transfer and recall and all(b['benefit'] for b in benefits),physical_validation=False,uncertainty_bound_status='UNKNOWN',scope='Separate eight-record synthetic development follow-up, never automatic feature or hardware promotion.')
