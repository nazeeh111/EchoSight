from pathlib import Path
import sys,json,importlib.util,hashlib
root=Path(__file__).resolve().parent.parent;p=root/'work/clock-refinement';sys.path.insert(0,str(p))
import runner
from echosight.multisource import infer_scene_bundle
spec=importlib.util.spec_from_file_location('frozen_eval',root/'work/review-de8442b-snapshot/evaluation/metrics.py');metrics=importlib.util.module_from_spec(spec);spec.loader.exec_module(metrics)
report=json.loads((p/'postfreeze-scenes/report.json').read_text());rerun=[]
for case in ['single_room-2441','near_reflector-2441']:
 folder=runner.SOURCE/'run-v4/fresh'/case;bundle=json.loads((folder/'bundle.json').read_text());answers={}
 for side in ['original','candidate']:
  stored=json.loads((p/'postfreeze-scenes'/f'run-v4-{case}-{side}.json').read_text());result=infer_scene_bundle(stored['processed_sessions'],bundle)
  assert result['surfaces']==stored['surfaces'];answers[side]=result
 truth=json.loads((folder/'truth.json').read_text());rerun.append({'case':case,'scores':{side:{k:metrics.score_surfaces(result,truth)[k] for k in ['matched_count','false_surfaces','missed_surfaces']} for side,result in answers.items()}})
totals={side:dict(matched_count=0,false_surfaces=0,missed_surfaces=0) for side in ['original','candidate']};coverage={side:dict(offset=0,normal=0,total=0) for side in totals};changed=[]
for row in report['rows']:
 truth=json.loads((runner.SOURCE/row['cohort']/'fresh'/row['key']/'truth.json').read_text())
 for side in totals:
  result=json.loads((p/'postfreeze-scenes'/f"{row['cohort']}-{row['key']}-{side}.json").read_text());score=metrics.score_surfaces(result,truth)
  assert score==row['scores'][side]
  for k in totals[side]:totals[side][k]+=score[k]
  for match in score['matches']:
   coverage[side]['total']+=1;coverage[side]['offset']+=bool(match['offset_95pct_covered']);coverage[side]['normal']+=bool(match['normal_95pct_covered'])
 if any(row['scores']['original'][k]!=row['scores']['candidate'][k] for k in totals['original']):changed.append([row['cohort'],row['key']])
summary={'all_stored_scene_scores_independently_recomputed':24,'changed_case_counts':changed,'totals':totals,'conditional_coverage_counts_not_empirical_calibration':coverage,'two_scoped_same_mapper_reruns':rerun,'scene_report_sha256':hashlib.sha256((p/'postfreeze-scenes/report.json').read_bytes()).hexdigest()}
(root/'work/clock-refinement-independent-spatial-check.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
