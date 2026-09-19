from pathlib import Path
import json,sys,copy,hashlib,subprocess
P=Path(__file__).resolve().parent;S=P/'source';sys.path.insert(0,str(S))
from tests.test_schemas import validator
from tests.test_evolution import result
from echosight.evolution import compare_results
out=json.loads((P/'cli-cancelled.json').read_text());validator('controlled-result').validate(out)
a=result();b=copy.deepcopy(a);c=copy.deepcopy(a)
a['result_id']='a';b['result_id']='b';c['result_id']='c'
b['session_id']='other-session';b['acquisition'].pop('session_id',None)
ab=compare_results(a,b);validator('comparison').validate(ab)
legacy=copy.deepcopy(ab);legacy['schema_version']='1.0'
for key in ('previous_session_id','current_session_id','support_comparison_status','new_capture_references'):legacy.pop(key,None)
for pair in legacy['correspondences']:
 for key in ('additional_support_references','lost_support_references'):pair.pop(key,None)
validator('comparison').validate(legacy)
carried=compare_results(b,c,previous_comparison=legacy);validator('comparison').validate(carried)
missing=copy.deepcopy(a);missing.pop('session_id',None);missing['acquisition'].pop('session_id',None)
unknown=compare_results(missing,b);validator('comparison').validate(unknown)
cancelled=copy.deepcopy(a);cancelled['status']='cancelled'
blocked=compare_results(a,cancelled);validator('comparison').validate(blocked)
report=dict(cancelled_controlled_claims_schema_valid=True,comparison_version=ab['schema_version'],cross_session_additional_support=[x['additional_support_count'] for x in ab['correspondences']],legacy_carry_status=carried['status'],legacy_carry_version=carried['schema_version'],missing_scope_counts=[x['additional_support_count'] for x in unknown['correspondences']],cancelled_compare_status=blocked['status'],cancelled_compare_tracks=blocked['current_tracks'])
(P/'schema-probe-results.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
