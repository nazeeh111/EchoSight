"""Cancelled scene schema must not admit completed material/color claims."""
import copy,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from tests.test_schemas import validator
cancelled=json.loads(Path('work/material-review/lifecycle-artifacts/terminal_callback.json').read_text())
example=json.loads(Path('examples/frontend/material-room.json').read_text())
claim=next(copy.deepcopy(x) for x in example['interpretation']['surface_interpretations'] if x['material']['status']=='estimated')
cancelled['interpretation']=dict(schema_version='1.0',status='complete',context_id=example['interpretation']['context_id'],source_result_id=cancelled['result_id'],surface_interpretations=[claim])
errors=list(validator('result').iter_errors(cancelled))
report={'scene_status':cancelled['status'],'material_status':claim['material']['status'],'appearance_status':claim['appearance']['status'],'schema_errors':[e.message for e in errors],'wrongly_accepted':not errors}
Path('work/material-review/cancel-schema-probe.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
