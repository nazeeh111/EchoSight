"""Frozen compatibility contrast only. No inference solver is imported or called."""
from pathlib import Path
import argparse,hashlib,json,subprocess,types
import numpy as np
from scipy.io import wavfile

HERE=Path(__file__).resolve().parent
CORE_COMMIT='de8442b2dd088c036d2b92eaeaf29a1273785795'
SIGNALS_SHA='2fdc6c5d48f8e55efc1650eb52a9ffbc6880e4efa767dbd449900fc38859747f'
PROTOCOL_SHA='7034d1cfa161791601d1bf11da75182978353b794d4b0e44e7f3118bd0fbe2cd'
SPEED=346.98
GATE=.075

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
def summary(rows):
 ncap=sum(r['nominal_capped'] for r in rows);npre=sum(r['nominal_precap'] for r in rows)
 pcap=sum(r['permuted_capped'] for r in rows);ppre=sum(r['permuted_precap'] for r in rows)
 added=lambda r,k:r[k+'_precap'] and not r[k+'_capped']
 return dict(opportunities=len(rows),nominal_capped=ncap,nominal_precap=npre,permuted_capped=pcap,permuted_precap=ppre,
             nominal_added=npre-ncap,permuted_added=ppre-pcap,additional_excess=(npre-ncap)-(ppre-pcap),
             capped_nominal_excess=ncap-pcap,precap_nominal_excess=npre-ppre,
             paired_added=dict(nominal_only=sum(added(r,'nominal') and not added(r,'permuted') for r in rows),
                               permuted_only=sum(added(r,'permuted') and not added(r,'nominal') for r in rows),
                               both=sum(added(r,'nominal') and added(r,'permuted') for r in rows),
                               neither=sum(not added(r,'nominal') and not added(r,'permuted') for r in rows)))

def predict(source,receiver,axis,offset):
 n=np.eye(3)[axis]
 assert (source@n-offset)*(receiver@n-offset)>0
 image=source+2*(offset-source@n)*n
 fraction=(offset-n@receiver)/(n@(image-receiver))
 assert 0<fraction<1
 bounce=receiver+fraction*(image-receiver)
 assert np.all(bounce>=-1e-6) and np.all(bounce<=np.array([5.705,5.965,2.355])+1e-6)
 return float((np.linalg.norm(image-receiver)-np.linalg.norm(source-receiver))/SPEED)

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dataset-work',type=Path,default=HERE.parents[1]/'work/measured-multisource');p.add_argument('--core',type=Path);p.add_argument('--output',type=Path,default=HERE/'results');args=p.parse_args();root=args.dataset_work.resolve();out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
 assert digest(HERE/'PROTOCOL.json')==PROTOCOL_SHA
 if args.core:raw=(args.core/'echosight/signals.py').read_bytes()
 else:raw=subprocess.run(['git','show',CORE_COMMIT+':echosight/signals.py'],cwd=HERE.parents[1],capture_output=True,check=True).stdout
 assert hashlib.sha256(raw).hexdigest()==SIGNALS_SHA
 source=raw.decode();needle='    if len(candidates)>18:\n';assert source.count(needle)==1
 source=source.replace(needle,"    result['pre_budget_candidates']=[dict(c) for c in candidates]\n"+needle)
 signals=types.ModuleType('fixed_extractor_instrumentation');exec(compile(source,'fixed_extractor_instrumentation.py','exec'),signals.__dict__)
 primary_path=root/'results/joint_mapper.json';permutation_path=root/'results/shuffled_geometry.json';prior_path=root/'results/path-diagnostic-report.json'
 primary=json.loads(primary_path.read_text());control=json.loads(permutation_path.read_text());prior=json.loads(prior_path.read_text());nominal_prior=next(a for a in prior['arms'] if a['pose_arm']=='survey')
 prior_counts={(x['session_id'],x['capture_id']):x['count'] for x in prior['pre_budget_counts']}
 prior_rows={(x['session_id'],x['capture_id'],x['path']):x for x in nominal_prior['first_order']}
 rows=[];catalogs=[];sessions=primary['processed_sessions'];controls=control['processed_sessions'];assert len(sessions)==len(controls)==4
 for si,(item,wrong) in enumerate(zip(sessions,controls)):
  session=item['session'];s=np.array(session['source_position_m']);receivers=np.array([o['receiver_position_m'] for o in item['observations']]);assert len(receivers)==10
  permutation=np.roll(np.arange(10),3)
  for j,(capture,o,po) in enumerate(zip(session['captures'],item['observations'],wrong['observations'])):
   assert o['capture_id']==po['capture_id'];r=receivers[j];pr=receivers[permutation[j]];assert np.array_equal(pr,np.array(po['receiver_position_m']))
   path=Path(capture['recording_path'])
   if not path.exists():path=root/'recordings'/f'source{si+1}'/path.name
   assert digest(path)==o['recording_sha256']
   rate,y=wavfile.read(path);assert y.dtype==np.float32
   extracted=signals.process_recording(y,rate,session['probe'],capture['capture_id'],sound_speed_m_s=session['sound_speed_m_s'])
   assert extracted['candidates']==o['candidates'];assert po['candidates']==o['candidates']
   pre=extracted['pre_budget_candidates'];cap=o['candidates'];key=(session['session_id'],o['capture_id']);assert len(pre)==prior_counts[key]
   retained=[]
   for idx,c in enumerate(pre):
    matches=[d['candidate_id'] for d in cap if {k:v for k,v in d.items() if k!='candidate_id'}==c];assert len(matches)<=1
    retained.append(dict(pre_budget_index=idx,retained_candidate_id=matches[0] if matches else None,**c))
   catalogs.append(dict(session_id=key[0],capture_id=key[1],recording_sha256=o['recording_sha256'],precap_count=len(pre),capped_count=len(cap),entries=retained))
   for axis,length in enumerate([5.705,5.965,2.355]):
    for side,offset in [('low',0),('high',length)]:
     surface=f'{axis}-{side}';record=dict(source_index=si+1,session_id=key[0],capture_id=key[1],surface_id=surface,precap_count=len(pre),capped_count=len(cap))
     for arm,receiver in [('nominal',r),('permuted',pr)]:
      delay=predict(s,receiver,axis,offset);record[arm+'_predicted_delay_s']=delay
      for kind,candidates in [('precap',pre),('capped',cap)]:
       errors=[abs(x['delay_s']-delay)*SPEED for x in candidates];indices=[i for i,e in enumerate(errors) if e<=GATE]
       record[arm+'_'+kind]=bool(indices);record[arm+'_'+kind+'_nearest_residual_m']=float(min(errors))
       record[arm+'_'+kind+'_compatible_catalog_indices']=indices
     prev=prior_rows[(key[0],key[1],surface)]
     assert record['nominal_capped']==prev['compatible_capped'] and record['nominal_precap']==prev['compatible_uncapped']
     rows.append(record)
 assert len(rows)==240
 groups=dict(source={},surface={},source_surface={},source_capture={})
 for r in rows:
  for level,key in [('source',str(r['source_index'])),('surface',r['surface_id']),('source_surface',str(r['source_index'])+'/'+r['surface_id']),('source_capture',str(r['source_index'])+'/'+r['capture_id'])]:groups[level].setdefault(key,[]).append(r)
 strata={level:{key:summary(subset) for key,subset in group.items()} for level,group in groups.items()}
 dump(out/'catalogs.json',catalogs);dump(out/'opportunities.json',rows)
 report=dict(protocol_sha256=PROTOCOL_SHA,core_commit=CORE_COMMIT,signals_sha256=SIGNALS_SHA,helper_sha256=digest(Path(__file__)),inputs_sha256={p.name:digest(p) for p in [primary_path,permutation_path,prior_path]},all40_capped_candidate_dictionaries_exact=True,all40_precap_counts_unchanged=True,all240_nominal_compatibilities_reproduced=True,control_positions_exactly_match_existing_permutation=True,catalogs_sha256=digest(out/'catalogs.json'),opportunities_sha256=digest(out/'opportunities.json'),overall=summary(rows),strata=strata,interpretation='Descriptive equal-density geometry compatibility only; not measured recall or a calibrated probability; fixed wrong-posecontrol is not perfectly exchangeable.',new_recordings=0,inverse_fits=0)
 dump(out/'report.json',report);print(json.dumps(report['overall'],indent=2))

if __name__=='__main__':main()
