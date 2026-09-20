"""Independent focused material review probes. Run from repository root."""
import copy, hashlib, json, math, sys
from pathlib import Path
from unittest.mock import patch
import numpy as np
from scipy.signal import fftconvolve
from scipy.stats import multivariate_normal
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from echosight.interpretation import interpret_scene, build_material_profile
from echosight.material_features import extract_surface_features, FEATURE_VERSION
from echosight.signals import generate_probe, process_recording
from echosight.geometry import image_source, reflection_point

results={}
def h(text):return hashlib.sha256(text.encode()).hexdigest()
def profile(name,mean,cov,prior):
 return dict(material_id=name,label=name,feature_version=FEATURE_VERSION,probe_sha256=h('probe'),route_id='chain',incidence_angle_range_deg=[10,70],mean_db=mean,predictive_covariance_db2=cov,prior_weight=prior,training_recording_sha256=[h(name+'trainingbytes')],training_waveform_sha256=[h(name+'trainingwave')],provenance=dict(kind='supplied',note='Review arithmetic only'))
def row(i,x):
 return dict(capture_id=f'c{i}',candidate_id=f'e{i}',recording_sha256=h(f'b{i}'),waveform_sha256=h(f'w{i}'),feature_version=FEATURE_VERSION,probe_sha256=h('probe'),incidence_angle_deg=35,status='ok',diagnostic_codes=[],feature_db=x)
scene=dict(result_id='review',status='partial',surfaces=[dict(surface_id='s',support=[])])
a=np.array([[2,.7,0,.3],[.7,1.5,.2,0],[0,.2,3,.4],[.3,0,.4,1.]])
b=np.array([[1.2,-.4,.1,0],[-.4,2.2,0,.2],[.1,0,1.1,-.2],[0,.2,-.2,2.]])
profiles=[profile('a',[0,-1,1,2],a.tolist(),.25),profile('b',[1,0,2,0],b.tolist(),.75)]
ctx=dict(schema_version='1.0',route_id='chain',profiles=profiles,maximum_squared_distance=100,minimum_views=1)
def run(rows,context=ctx):
 before=copy.deepcopy(scene)
 with patch('echosight.interpretation.extract_surface_features',return_value=rows):out=interpret_scene(scene,context)['surface_interpretations'][0]
 assert scene==before
 return out
xs=[[.2,-.3,1.1,.5],[1.4,.6,1.8,-.4]]
oracles=[]
for x in xs:
 q=np.array([p['prior_weight']*multivariate_normal.pdf(x,mean=p['mean_db'],cov=p['predictive_covariance_db2']) for p in profiles]);oracles.append(q/q.sum())
out=run([row(i,x) for i,x in enumerate(xs)])
actual=np.array([p['probability'] for p in out['material']['probabilities']]);expected=np.mean(oracles,axis=0)
np.testing.assert_allclose(actual,expected,rtol=1e-12)
results['non_diagonal_gaussian_equal_view_mixture']={'expected':expected.tolist(),'actual':actual.tolist()}
# Identical models isolate prior and contextual palette mass exactly.
c=copy.deepcopy(ctx);c['profiles'][1]['mean_db']=c['profiles'][0]['mean_db'];c['profiles'][1]['predictive_covariance_db2']=c['profiles'][0]['predictive_covariance_db2']
c['profiles'][0]['appearance']=dict(provenance=dict(kind='supplied',note='Review palette'),colors=[dict(color_srgb='#FF0000',probability=.6),dict(color_srgb='#0000FF',probability=.2)])
o=run([row(1,xs[0])],c);colors={x['color_srgb']:x['probability'] for x in o['appearance']['colors']}
np.testing.assert_allclose([colors['#FF0000'],colors['#0000FF'],o['appearance']['unassigned_probability']],[.15,.05,.8],atol=1e-14)
results['palette_mass']=o['appearance']
checks={}
for mode in ['route','angle','missing_angle','probe','training_overlap_in_incompatible_profile','duplicate_bytes','duplicate_waves','minimum_views','outlier']:
 c=copy.deepcopy(ctx);rows=[row(1,xs[0])]
 if mode=='route':c['route_id']='different'
 if mode=='angle':rows[0]['incidence_angle_deg']=71
 if mode=='missing_angle':rows[0].pop('incidence_angle_deg')
 if mode=='probe':rows[0]['probe_sha256']=h('other')
 if mode=='training_overlap_in_incompatible_profile':c['profiles'][1]['route_id']='different';c['profiles'][1]['training_waveform_sha256']=[rows[0]['waveform_sha256']]
 if mode.startswith('duplicate_'):
  rows.append(row(2,xs[1]));key='recording_sha256' if mode=='duplicate_bytes' else 'waveform_sha256';rows[1][key]=rows[0][key]
 if mode=='minimum_views':c['minimum_views']=2
 if mode=='outlier':rows[0]['feature_db']=[400]*4
 o=run(rows,c);assert o['material']['status']=='unknown' and not o['material']['probabilities'] and not o['appearance']['colors'],(mode,o)
 assert len(o['feature_records'])==len(rows)
 checks[mode]=[r['diagnostic_codes'] for r in o['feature_records']]
results['negative_admission']=checks
# Independent explicit centered cross-product formula for the profile builder.
vectors=np.array([[0,1,2,0],[2,0,1,1],[1,3,0,2],[-1,2,3,1],[3,-1,2,4],[2,2,1,-1]],dtype=float)
reference_rows=[row(i+10,x.tolist()) for i,x in enumerate(vectors)]
with patch('echosight.interpretation.extract_surface_features',return_value=reference_rows):
 fitted=build_material_profile(scene,'s',material_id='fitted',label='Review fit',route_id='chain',regularization_std_db=.4,provenance=dict(kind='supplied',note='Review vectors'))
mean=sum(vectors)/len(vectors);covariance=sum(np.outer(x-mean,x-mean) for x in vectors)/(len(vectors)-1)+np.eye(4)*.16
np.testing.assert_allclose(fitted['mean_db'],mean,rtol=1e-12)
np.testing.assert_allclose(fitted['predictive_covariance_db2'],covariance,rtol=1e-12)
assert fitted['reference_summary']['sample_count']==len(vectors)
assert fitted['training_waveform_sha256']==[r['waveform_sha256'] for r in reference_rows]
results['profile_fit']={'mean':fitted['mean_db'],'covariance':fitted['predictive_covariance_db2'],'sample_count':len(vectors),'regularization_variance':.16}
# Raw rendering with independent geometry and exact 1/d pressure amplitudes.
wave,probe=generate_probe(dict(high_hz=14000.));fs=probe['sample_rate_hz'];source=np.array([1.5,1.5,1.3]);normal=np.array([1.,0.,0.]);image=image_source(source,normal,0.)
features=[]
for i,(receiver,reflection) in enumerate([(np.array([.7,2.4,1.9]),.3),(np.array([1.1,2.8,.8]),.3),(np.array([.7,2.4,1.9]),-.6)]):
 direct=np.linalg.norm(receiver-source);reflected=np.linalg.norm(receiver-image);impulse=np.zeros(round(.12*fs))
 for distance,coefficient in [(direct,.5/direct),(reflected,.5*reflection/reflected)]:
  delay=distance/343*fs;indices=np.arange(math.floor(delay)-40,math.floor(delay)+41);kernel=np.sinc(indices-delay)*np.hanning(81);kernel/=kernel.sum();impulse[indices]+=coefficient*kernel
 samples=np.r_[np.zeros(round(.06*fs)),fftconvolve(wave,impulse),np.zeros(round(.04*fs))]
 samples+=np.random.default_rng(738+i).normal(0,2e-6,len(samples))
 obs=process_recording(samples,fs,probe,f'raw{i}');assert obs['status']=='ok' and len(obs['candidates'])==1
 obs.update(receiver_position_m=receiver.tolist(),recording_sha256=h(f'rawbytes{i}'),waveform_sha256=h(f'rawwave{i}'))
 candidate=obs['candidates'][0]
 surface=dict(surface_id='rawsurface',model_status='conditional_first_order_hypothesis',normal=normal.tolist(),offset_m=0.,image_source_m=image.tolist(),support=[dict(capture_id=f'raw{i}',candidate_id=candidate['candidate_id'],observed_delay_s=candidate['delay_s'],predicted_delay_s=(reflected-direct)/343.,reflection_point_m=reflection_point(source,receiver,normal,0.).tolist())])
 rawscene=dict(status='partial',surfaces=[surface],observations=[obs],acquisition=dict(source_position_m=source.tolist(),coordinate_frame_id='review',sound_speed_m_s=343.,probe=probe,captures=[dict(capture_id=f'raw{i}',receiver_position_m=receiver.tolist())]))
 r=extract_surface_features(rawscene,surface)[0];assert r['status']=='ok',r
 np.testing.assert_allclose(r['feature_db'],20*math.log10(abs(reflection)),atol=.45)
 features.append(r['feature_db'])
results['raw_inverse_distance_and_polarity']={'feature_db':features,'expected_db':[20*math.log10(.3),20*math.log10(.3),20*math.log10(.6)],'max_abs_error_db':max(np.max(abs(np.array(x)-y)) for x,y in zip(features,[20*math.log10(.3),20*math.log10(.3),20*math.log10(.6)]))}
files=['echosight/'+x+'.py' for x in ['material_features','interpretation','pipeline','inference','storage','api','cli']]+['schemas/'+x+'.schema.json' for x in ['interpretation-context','interpretation-result','session','calibration-patch','result']]
results['reviewed_file_sha256']={f:hashlib.sha256(Path(f).read_bytes()).hexdigest() for f in files}
Path('work/material-review/probe-results.json').write_text(json.dumps(results,indent=2,allow_nan=False)+'\n')
print(json.dumps({'status':'passed','checks':list(results)[:-1],'raw_max_abs_error_db':results['raw_inverse_distance_and_polarity']['max_abs_error_db']},indent=2))
