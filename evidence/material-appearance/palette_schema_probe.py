"""A valid nine-profile shared palette must yield a schema-valid probability."""
import copy,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from tests.test_material_features import MaterialFeatureTests
from echosight.material_features import extract_surface_features,FEATURE_VERSION
from echosight.interpretation import interpret_scene,validate_context
from tests.test_schemas import validator
MaterialFeatureTests.setUpClass();result=copy.deepcopy(MaterialFeatureTests.result)
row=extract_surface_features(result,result['surfaces'][0])[0];assert row['status']=='ok'
profiles=[]
for i in range(9):
 h=lambda s:hashlib.sha256(s.encode()).hexdigest()
 profiles.append(dict(material_id='profile'+str(i),label='Supplied '+str(i),route_id='chain',feature_version=FEATURE_VERSION,probe_sha256=row['probe_sha256'],incidence_angle_range_deg=[0,90],mean_db=row['feature_db'],predictive_covariance_db2=[[int(a==b) for b in range(4)] for a in range(4)],prior_weight=1,training_recording_sha256=[h('bytes'+str(i))],training_waveform_sha256=[h('waves'+str(i))],provenance=dict(kind='supplied',note='Review valid profiles'),appearance=dict(provenance=dict(kind='supplied',note='Shared palette'),colors=[dict(color_srgb='#FF0000',probability=1)])))
ctx=validate_context(dict(schema_version='1.0',route_id='chain',profiles=profiles,maximum_squared_distance=16,minimum_views=1))
out=interpret_scene(result,ctx);errors=list(validator('interpretation-result').iter_errors(out))
report=dict(appearance=out['surface_interpretations'][0]['appearance'],errors=[e.message for e in errors],schema_valid=not errors)
Path('work/material-review/palette-schema-probe.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
