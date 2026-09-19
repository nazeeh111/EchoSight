"""Evaluation-only measured path attribution and echo-refined pose sensitivity."""
from pathlib import Path
import copy,itertools,json,types,time
import numpy as np
from evaluation import dechorate_multisource as base


def poses():
    R=base.ROOT
    spec=json.loads((R/'diagnostic-protocol.json').read_text());hashspec=base.digest(R/'diagnostic-protocol.json')
    original=json.loads((R/'results/joint_mapper.json').read_text())['processed_sessions'];refined=copy.deepcopy(original)
    metadata=json.loads((R/'metadata-audit.json').read_text());conventions=[]
    for i,item in enumerate(refined):
     source=[];receivers=[]
     for j in range(2):
      path=R/'data'/metadata[2*i+j]['filename']
      with base.h5py.File(path,'r') as f:
       row={name:{str(k):base.decode(v) for k,v in f[name].attrs.items()} for name in ['SourcePosition','ReceiverPosition','Data.SamplingRate']};conventions.append(dict(file=path.name,datasets=row))
       for name in ['SourcePosition','ReceiverPosition']:
        assert row[name]['Units']=='metre' and row[name]['Type']=='cartesian'
       source.append(np.asarray(f['SourcePosition'][0]));receivers.extend(np.asarray(f['ReceiverPosition'][:,:,0]))
     assert np.allclose(source[0],source[1]);item['session']['source_position_m']=source[0].tolist()
     for j,r in enumerate(receivers):
      item['session']['captures'][j]['receiver_position_m']=r.tolist();item['observations'][j]['receiver_position_m']=r.tolist()
    rows=[]
    for label,processed in [('survey',original),('echo_refined',refined)]:
     for item in processed:
      session=item['session'];s=np.array(session['source_position_m']);errors=[]
      for o in item['observations']:
       errors.append(o['direct_arrival_receiver_s']-session['probe']['lead_s']-np.linalg.norm(s-o['receiver_position_m'])/346.98)
      values=np.array(errors);center=np.median(values)
      rows.append(dict(pose_arm=label,session_id=session['session_id'],direct_reference_model_residual_s=errors,source_constant_latency_median_s=float(center),remaining_rms_s=float(np.sqrt(np.mean((values-center)**2))),remaining_max_abs_s=float(np.max(abs(values-center)))))
    base.dump(R/'diagnostic-conventions.json',dict(protocol_sha256=hashspec,datasets=conventions,direct_reference=rows))
    bundle=json.loads((R/'bundle.json').read_text());fits=[];before=base.codehash()
    for method in ['mapper','plane_grid']:
     start=time.perf_counter();result=base.infer_scene_bundle(refined,bundle,method=method);duration=time.perf_counter()-start;base.dump(R/'results'/f'echo-refined-{method}.json',result);fits.append(dict(method=method,runtime_seconds=duration,result=result))
    dims=np.asarray(base.REFERENCE['room_size_m'])
    truth=dict(surfaces=[dict(surface_id=f'{axis}-{side}',normal=np.eye(3)[axis].tolist(),offset_m=float(value)) for axis in range(3) for side,value in [('low',0),('high',dims[axis])]])
    for f in fits:
     f['metrics']=base.score_surfaces(f['result'],truth)
     for match in f['metrics']['matches']:match['offset_95pct_covered']=None;match['normal_95pct_covered']=None
     f['status']=f['result']['status'];f['surface_count']=len(f['result']['surfaces']);del f['result']
    base.dump(R/'results/diagnostic-report.json',dict(protocol_sha256=hashspec,protocol=spec,source_unchanged=before==base.codehash(),source_sha256=before,runner_sha256=base.digest(Path(__file__)),fits=fits,direct_reference=rows,primary_failure_unchanged=True))
    print(json.dumps(fits,indent=2))


def paths():
    R=base.ROOT
    base.dump=lambda p,o:p.write_text(json.dumps(o,indent=2,allow_nan=False,default=lambda x:x.item())+'\n')
    from echosight.geometry import reflection_path
    from echosight.storage import read_recording_snapshot
    source=(base.CORE/'echosight/signals.py').read_text()
    needle='    if len(candidates)>18:\n'
    assert source.count(needle)==1
    source=source.replace(needle,"    result['pre_budget_candidates']=[dict(c) for c in candidates]\n"+needle)
    module=types.ModuleType('instrumented_frozen_signals');exec(compile(source,'instrumented_frozen_signals.py','exec'),module.__dict__)
    main=json.loads((R/'results/joint_mapper.json').read_text());meta=json.loads((R/'metadata-audit.json').read_text());processed=main['processed_sessions'];uncapped={};equal=True
    for item in processed:
     ses=item['session']
     for cap,original in zip(ses['captures'],item['observations']):
      samples,rate,_=read_recording_snapshot(cap['recording_path']);o=module.process_recording(samples,rate,ses['probe'],cap['capture_id'],sound_speed_m_s=ses['sound_speed_m_s'])
      assert o['candidates']==original['candidates'];uncapped[(ses['session_id'],cap['capture_id'])]=o['pre_budget_candidates']
    refined=copy.deepcopy(processed)
    for i,item in enumerate(refined):
     item['session']['source_position_m']=np.asarray(meta[2*i]['source_position_echo_refined'])[0].tolist()
     rr=np.concatenate([np.asarray(meta[2*i+j]['receiver_position_echo_refined'])[:,:,0] for j in range(2)])
     for j,o in enumerate(item['observations']):o['receiver_position_m']=rr[j].tolist()
    # Supplied room reference enters only this evaluation diagnostic.
    dims=np.array(base.REFERENCE['room_size_m']);planes=[(np.eye(3)[a],v,f'{a}-{side}') for a in range(3) for side,v in [('low',0),('high',dims[a])]]
    paths=[[i] for i in range(6)]+[list(x) for x in itertools.permutations(range(6),2)]
    def predictions(s,r):
     result=[]
     for ids in paths:
      pp=reflection_path(s,r,[(planes[i][0],planes[i][1]) for i in ids])
      if pp is None:continue
      points=np.asarray(pp['vertices_m'])[1:-1]
      if np.any(points< -1e-6) or np.any(points>dims+1e-6):continue
      result.append(dict(label=' then '.join(planes[i][2] for i in ids),order=len(ids),delay_s=(pp['length_m']-np.linalg.norm(s-r))/346.98))
     return result
    report=[]
    for label,items in [('survey',processed),('echo_refined',refined)]:
     pp={};caps={};first=[]
     for item in items:
      ses=item['session'];s=np.array(ses['source_position_m'])
      for o in item['observations']:
       key=(ses['session_id'],o['capture_id']);pred=predictions(s,np.array(o['receiver_position_m']));pp[key]=pred;caps[key]=o['candidates']
       for p in pred:
        if p['order']!=1:continue
        def closest(c):return min((abs(x['delay_s']-p['delay_s'])*346.98 for x in c),default=None)
        a=closest(o['candidates']);b=closest(uncapped[key]);first.append(dict(session_id=key[0],capture_id=key[1],path=p['label'],capped_nearest_m=a,pre_budget_nearest_m=b,compatible_capped=a is not None and a<=.075,compatible_uncapped=b is not None and b<=.075,lost_compatible_due_to_cap=(a is None or a>.075) and b is not None and b<=.075))
     surfaces=[]
     # Attribute original primarysupports in both coordinatearms; refinedfitseparately has its own result.
     for surface in main['surfaces']:
      supports=[];families={}
      for link in surface['support']:
       key=(link['session_id'],link['capture_id']);models=pp[key];dist=[abs(link['delay_s']-x['delay_s'])*346.98 for x in models];nearest=int(np.argmin(dist));valid=[m['label'] for m,d in zip(models,dist) if d<=.075]
       for family in valid:families[family]=families.get(family,0)+1
       supports.append(dict(session_id=key[0],capture_id=key[1],candidate_id=link['candidate_id'],nearest_path=models[nearest]['label'],nearest_residual_m=dist[nearest],compatible_paths=valid))
      surfaces.append(dict(surface_id=surface['surface_id'],normal=surface['normal'],offset_m=surface['offset_m'],support_count=len(supports),compatible_support_count=sum(bool(x['compatible_paths']) for x in supports),family_counts=families,supports=supports))
     report.append(dict(pose_arm=label,first_order_prediction_count=len(first),first_order_compatible_capped=sum(x['compatible_capped'] for x in first),first_order_compatible_uncapped=sum(x['compatible_uncapped'] for x in first),lost_compatible_due_to_cap=sum(x['lost_compatible_due_to_cap'] for x in first),first_order=first,surfaces=surfaces))
    base.dump(R/'results/path-diagnostic-report.json',dict(protocol_sha256=base.digest(R/'path-diagnostic-protocol.json'),instrumented_core_source_sha256=base.digest(base.CORE/'echosight/signals.py'),instrumentation='Only records copiesof pre-budget candidates; returned capped candidates exactlyequal original40 observations.',all40_capped_candidates_identical=True,pre_budget_counts=[dict(session_id=k[0],capture_id=k[1],count=len(v)) for k,v in uncapped.items()],arms=report,not_independent_echo_labels=True))
    for a in report:
     print(a['pose_arm'],'firstorder',a['first_order_compatible_capped'],a['first_order_compatible_uncapped'],'caploss',a['lost_compatible_due_to_cap'],'total',a['first_order_prediction_count'])
     for s in a['surfaces']:print(s['surface_id'],s['compatible_support_count'],s['support_count'],s['family_counts'])


def main():
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['poses','paths'])
    parser.add_argument('--workspace',required=True)
    parser.add_argument('--core',default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument('--core-commit',default='de8442b2dd088c036d2b92eaeaf29a1273785795')
    parser.add_argument('--allow-different-core',action='store_true')
    parser.add_argument('--h5py-path')
    args=parser.parse_args();base.configure(args)
    payload=Path(__file__).with_name('dechorate_multisource_path_protocol.json').read_bytes()
    target=base.ROOT/'path-diagnostic-protocol.json'
    if target.exists() and target.read_bytes()!=payload:raise ValueError('Changed path diagnostic protocol')
    target.write_bytes(payload)
    if args.action=='poses':poses()
    else:paths()

if __name__=='__main__':main()
