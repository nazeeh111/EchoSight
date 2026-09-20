"""Synthetic model arithmetic and public boundaries; not material accuracy."""
import copy,json,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from echosight.interpretation import validate_context,context_fingerprint,interpret_scene,build_material_profile
VERSION='apparent-reflection-bands-v1'
def profile(name='a',mean=0):
 return dict(material_id=name,label='Synthetic '+name,feature_version=VERSION,probe_sha256='1'*64,route_id='test-route',incidence_angle_range_deg=[0,90],mean_db=[mean]*4,predictive_covariance_db2=np.eye(4).tolist(),prior_weight=1,training_recording_sha256=['a'*64],training_waveform_sha256=['b'*64],provenance={'kind':'simulated','note':'Arithmetic fixture'})
def context():return dict(schema_version='1.0',route_id='test-route',profiles=[profile(),profile('b',1)],maximum_squared_distance=16,minimum_views=1)
def row(i=1,x=None):return dict(capture_id=f'capture-{i}',candidate_id=f'candidate-{i}',recording_sha256=f'{i:064x}',waveform_sha256=f'{i+100:064x}',feature_version=VERSION,probe_sha256='1'*64,status='ok',diagnostic_codes=[],incidence_angle_deg=30,feature_db=[0]*4 if x is None else x)
def scene():return dict(result_id='result-test',status='partial',surfaces=[{'surface_id':'surface-test','support':[]}])
class InterpretationTests(unittest.TestCase):
 def apply(self,rows,ctx=None):
  s=scene();before=copy.deepcopy(s)
  with patch('echosight.interpretation.extract_surface_features',return_value=rows):r=interpret_scene(s,context() if ctx is None else ctx)
  self.assertEqual(s,before);return r['surface_interpretations'][0]
 def test_gaussian_and_color_mixture(self):
  c=context();c['profiles'][0]['appearance']={'provenance':{'kind':'supplied','note':'Synthetic context'},'colors':[{'color_srgb':'#ffffff','probability':.8},{'color_srgb':'#000000','probability':.2}]}
  out=self.apply([row()],c);p={x['material_id']:x['probability'] for x in out['material']['probabilities']};expected=1/(1+np.exp(-2));self.assertAlmostEqual(p['a'],expected)
  colors={x['color_srgb']:x['probability'] for x in out['appearance']['colors']};self.assertAlmostEqual(colors['#FFFFFF'],.8*expected);self.assertAlmostEqual(out['appearance']['unassigned_probability'],1-expected)
 def test_covariance_determinant(self):
  c=context();c['profiles'][1]['mean_db']=[0]*4;c['profiles'][1]['predictive_covariance_db2']=(np.eye(4)*4).tolist();self.assertAlmostEqual(self.apply([row()],c)['material']['probabilities'][0]['probability'],16/17)
 def test_outlier_and_missing_view_mass(self):
  out=self.apply([row(x=[10]*4)]);self.assertEqual(out['material']['probabilities'],[]);self.assertEqual(out['appearance']['unassigned_probability'],1)
  bad=row(2);bad.update(status='unknown',diagnostic_codes=['overlap']);bad.pop('feature_db');out=self.apply([row(),bad]);self.assertEqual(out['material']['total_views'],2);self.assertEqual(out['material']['valid_views'],1);self.assertAlmostEqual(sum(p['probability'] for p in out['material']['probabilities']),1);self.assertEqual(out['material']['evidence_coverage'],.5);self.assertEqual(out['material']['unassigned_view_weight'],.5);self.assertNotIn('unassigned_probability',out['material'])
 def test_overlap_across_library_and_duplicate_queries(self):
  c=context();c['profiles'][1]['training_waveform_sha256']=[row()['waveform_sha256']];out=self.apply([row()],c);self.assertIn('reference_query_overlap',out['feature_records'][0]['diagnostic_codes']);self.assertEqual(out['material']['status'],'unknown')
  r=row();other=row(2);other['waveform_sha256']=r['waveform_sha256'];self.assertEqual(self.apply([r,other])['material']['valid_views'],0)
 def test_route_angle_and_minimum_views(self):
  for mode in ('route','angle','count'):
   c=context()
   if mode=='route':c['route_id']='other'
   if mode=='angle':
    for p in c['profiles']:p['incidence_angle_range_deg']=[40,60]
   if mode=='count':c['minimum_views']=2
   self.assertEqual(self.apply([row()],c)['material']['status'],'unknown')
 def test_context_strict_and_canonical(self):
  c=context();before=copy.deepcopy(c);canonical=validate_context(c);canonical['profiles'][0]['mean_db'][0]=7;self.assertEqual(c,before);self.assertEqual(context_fingerprint(c),context_fingerprint(json.loads(json.dumps(c,sort_keys=True))))
  mutations=[lambda c:c.update(extra=True),lambda c:c.update(minimum_views=True),lambda c:c.update(maximum_squared_distance=float('nan')),lambda c:c['profiles'][0].update(prior_weight=False),lambda c:c['profiles'][0].update(training_recording_sha256=['wrong']),lambda c:c['profiles'][0].update(predictive_covariance_db2=np.zeros((4,4)).tolist()),lambda c:c['profiles'][0].update(predictive_covariance_db2=[[1,2,0,0],[2,1,0,0],[0,0,1,0],[0,0,0,1]]),lambda c:c['profiles'][0].update(appearance={'provenance':{'kind':'supplied','note':'x'},'colors':[{'color_srgb':'#GG0000','probability':1}]})]
  for mutation in mutations:
   c=context();mutation(c)
   with self.subTest(mutation=mutation),self.assertRaises(ValueError):validate_context(c)
 def test_absence_and_cancellation(self):
  self.assertIsNone(validate_context(None));self.assertIsNone(context_fingerprint(None));self.assertEqual(interpret_scene(scene(),None)['status'],'not_configured');self.assertEqual(interpret_scene({'surfaces':[]},context())['status'],'no_geometry')
  r=interpret_scene(scene(),context(),cancel=lambda:True);self.assertEqual(r['status'],'cancelled');self.assertEqual(r['surface_interpretations'],[])
  bad=row();bad.update(status='unknown',diagnostic_codes=['cancelled']);bad.pop('feature_db')
  with patch('echosight.interpretation.extract_surface_features',return_value=[bad]):r=interpret_scene(scene(),context())
  self.assertEqual(r['status'],'cancelled');self.assertEqual(r['surface_interpretations'],[])
 def test_profile_builder_sample_covariance(self):
  vectors=np.vstack([np.zeros(4),np.eye(4)]);rows=[row(i+1,x.tolist()) for i,x in enumerate(vectors)]
  with patch('echosight.interpretation.extract_surface_features',return_value=rows):p=build_material_profile(scene(),'surface-test',material_id='test',label='Test',route_id='test-route',regularization_std_db=.5,provenance={'kind':'simulated','note':'Known label fixture'})
  np.testing.assert_allclose(p['mean_db'],vectors.mean(0));np.testing.assert_allclose(p['predictive_covariance_db2'],np.cov(vectors,rowvar=False)+np.eye(4)*.25);self.assertEqual(p['reference_summary']['sample_count'],5);c=context();c['profiles']=[p];validate_context(c)
 def test_profile_builder_singular_and_reused(self):
  for rows in ([row(i) for i in range(1,6)],[row()]*5):
   with patch('echosight.interpretation.extract_surface_features',return_value=rows),self.assertRaises(ValueError):build_material_profile(scene(),'surface-test',material_id='test',label='Test',route_id='test-route',provenance={'kind':'supplied','note':'x'})
 def test_extreme_narrow_profile_abstains_without_nonfinite_output(self):
  c=context()
  for p in c['profiles']:p['predictive_covariance_db2']=(np.eye(4)*1e-320).tolist()
  out=self.apply([row(x=[400]*4)],c);self.assertEqual(out['material']['status'],'unknown');json.dumps(out,allow_nan=False)
 def test_actual_feature_rows_satisfy_output_schema(self):
  from tests.test_material_features import MaterialFeatureTests
  from jsonschema import Draft202012Validator
  MaterialFeatureTests.setUpClass();c=context();c['profiles']=[]
  result=interpret_scene(MaterialFeatureTests.result,c)
  schema=json.loads((Path(__file__).resolve().parents[1]/'schemas/interpretation-result.schema.json').read_text())
  Draft202012Validator(schema).validate(result)
  self.assertEqual(result['surface_interpretations'][0]['material']['status'],'unknown')
 def test_nine_profile_palette_mass_stays_bounded_without_filling_missing_mass(self):
  from tests.test_material_features import MaterialFeatureTests
  from echosight.material_features import extract_surface_features
  from jsonschema import Draft202012Validator
  MaterialFeatureTests.setUpClass();result=copy.deepcopy(MaterialFeatureTests.result)
  feature=extract_surface_features(result,result['surfaces'][0])[0];self.assertEqual(feature['status'],'ok')
  schema=json.loads((Path(__file__).resolve().parents[1]/'schemas/interpretation-result.schema.json').read_text())
  for palette_weight,missing_palette in [(1.,False),(.8,False),(.8,True),(1.-1e-10,False)]:
   with self.subTest(palette_weight=palette_weight,missing_palette=missing_palette):
    c=context();c['profiles']=[]
    for i in range(9):
     p=profile('profile'+str(i));p.update(mean_db=feature['feature_db'],probe_sha256=feature['probe_sha256'])
     if not (missing_palette and i==8):p['appearance']={'provenance':{'kind':'supplied','note':'Regression palette'},'colors':[{'color_srgb':'#FF0000','probability':palette_weight}]}
     c['profiles'].append(p)
    out=interpret_scene(result,c);appearance=out['surface_interpretations'][0]['appearance'];expected=palette_weight*(8/9 if missing_palette else 1)
    Draft202012Validator(schema).validate(out)
    self.assertLessEqual(appearance['colors'][0]['probability'],1)
    self.assertAlmostEqual(appearance['colors'][0]['probability'],expected)
    self.assertAlmostEqual(appearance['unassigned_probability'],1-expected,delta=1e-15)
    if expected<1:self.assertGreater(appearance['unassigned_probability'],0)
 def test_offline_schemas(self):
  from jsonschema import Draft202012Validator
  root=Path(__file__).resolve().parents[1];c=context();Draft202012Validator(json.loads((root/'schemas/interpretation-context.schema.json').read_text())).validate(c)
  with patch('echosight.interpretation.extract_surface_features',return_value=[row()]):r=interpret_scene(scene(),c)
  validator=Draft202012Validator(json.loads((root/'schemas/interpretation-result.schema.json').read_text()));validator.validate(r);validator.validate(interpret_scene(scene(),None))
if __name__=='__main__':unittest.main()
