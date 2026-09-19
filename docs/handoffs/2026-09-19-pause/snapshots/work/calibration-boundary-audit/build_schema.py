from pathlib import Path
import json,copy
R=Path(__file__).resolve().parents[2]
base='https://echosight.local/schemas/'
def ref(uri):return {'$ref':base+uri}
def obj(properties,required=None):return {'type':'object','properties':properties,'required':list(properties) if required is None else required,'additionalProperties':False}
def arr(items,lo=0,hi=32):return {'type':'array','minItems':lo,'maxItems':hi,'items':items}
num={'type':'number'};text={'type':'string'};sha={'type':'string','pattern':'^[a-f0-9]{64}$'}
idref=ref('session-1.0.json#/$defs/id')
vec=arr(num,3,3)
reference=obj({'normal':dict(vec,description='Supplied unit normal, not inferred geometry; unit length checked by runtime.'),'offset_m':{'type':'number','minimum':-1000,'maximum':1000},'offset_std_m':{'type':'number','exclusiveMinimum':0,'maximum':.05},'normal_std_rad':{'type':'number','exclusiveMinimum':0,'maximum':.03},'source_search_radius_m':{'type':'number','minimum':.01,'maximum':.5,'default':.15},'effective_speed_bounds_m_s':arr({'type':'number','minimum':250,'maximum':460},2,2),'training_capture_ids':dict(arr(idref,8,28),uniqueItems=True),'validation_capture_ids':dict(arr(idref,4,24),uniqueItems=True)})
reference['properties']['effective_speed_bounds_m_s']['default']=[300.,380.]
request=copy.deepcopy(reference);request.update({'$schema':'https://json-schema.org/draft/2020-12/schema','$id':base+'calibration-reference-1.0.json','title':'EchoSight supplied reference calibration inputs v1','description':'Optional defaults are materialized in result snapshots. Runtime additionally checks unit normal, increasing speed bounds, disjoint full partition and source/receiver geometry.'})
request['required']=[k for k in reference['required'] if k not in ('source_search_radius_m','effective_speed_bounds_m_s')]
(R/'schemas/calibration-reference.schema.json').write_text(json.dumps(request,indent=2)+'\n')
session=json.loads((R/'schemas/session.schema.json').read_text())
keys=('schema_version','session_id','coordinate_frame_id','source_position_m','source_position_std_m','sound_speed_m_s','sound_speed_std_m_s','source_clock_scale','source_clock_std_ppm','effective_speed_m_s','source_effective_speed_covariance')
acqprops={k:ref('session-1.0.json#/properties/'+k) for k in keys}
probe_keys=('sample_rate_hz','duration_s','low_hz','high_hz','repetitions','period_s','lead_s','tail_s','max_echo_delay_s','schema_version','kind','sample_count','pilot_start_samples','waveform_sha256','timing_unit')
acqprops['probe']=obj({k:{} for k in probe_keys},[])
acqprops['probe']['description']='Only processor-consumed configuration/verification fields; missing or malformed declarations are retained for rejected results. The signal processor remains the validator.'
capture=obj({k:ref('session-1.0.json#/$defs/capture/properties/'+k) for k in ('capture_id','receiver_position_m','receiver_position_std_m','provenance')})
acqprops['captures']=arr(capture,12,32)
acq=obj(acqprops,['schema_version','coordinate_frame_id','source_position_m','source_position_std_m','sound_speed_m_s','sound_speed_std_m_s','source_clock_scale','source_clock_std_ppm','captures'])
inputs=obj({'reference':reference,'acquisition':acq})
record=obj({'capture_id':idref,'hash_status':{'enum':['verified','not_available','not_processed']},'sha256':{'anyOf':[sha,{'type':'null'}]}})
record['allOf']=[{'if':{'properties':{'hash_status':{'const':'verified'}}},'then':{'properties':{'sha256':sha}},'else':{'properties':{'sha256':{'type':'null'}}}}]
props={'schema_version':{'const':'1.1'},'status':{'enum':['calibration_proposal','rejected']},'physical_validation':{'const':False},'calibration_input':inputs,'recording_inputs':arr(record,12,32),'input_id':{'type':'string','pattern':'^calibration-input-[a-f0-9]{64}$'},'input_result_id':{'anyOf':[{'type':'string','pattern':'^result-[a-f0-9]{20}$'},{'type':'null'}]},'reference_geometry':text,'training_capture_ids':arr(idref,8,28),'validation_capture_ids':arr(idref,4,24),'diagnostics':arr({'anyOf':[text,{'type':'object','required':['code'],'properties':{'code':text,'message':text,'capture_id':idref,'eligible_candidates':{'type':'integer','minimum':0}},'additionalProperties':False}]},0,64),'clock_interpretation':text,'conditional_on':arr(text,1,16)}
props['provenance']={'allOf':[ref('result-1.0.json#/properties/provenance'),{'type':'object','required':['software_version','physical_validation','recordings','calibration_implementation_sha256'],'properties':{'software_version':text,'recordings':arr(obj({'capture_id':idref,'sha256':sha}),0,32),'calibration_implementation_sha256':sha}}]}
props['source_declaration_consistency']=ref('result-1.0.json#/properties/source_declaration_consistency')
props['information_singular_values']=arr({'type':'number','minimum':0},4,4)
for k in ('training_normalized_rms','validation_normalized_rms','validation_max_abs_z','validation_nominal_rms_s','validation_fitted_rms_s','validation_max_abs_residual_s'):props[k]={'type':'number','minimum':0}
props['evidence']=arr(obj({'capture_id':idref,'candidate_id':text,'observed_delay_s':num,'predicted_delay_s':num,'residual_s':num,'partition':{'enum':['training','validation']}}),12,32)
props['acceptance']=obj({k:{'const':v} for k,v in {'maximum_normalized_rms':2.5,'maximum_validation_abs_z':3.5,'maximum_validation_rms_s':.0001,'maximum_validation_abs_residual_s':.0002}.items()})
props['calibration']=obj({k:ref('calibration-patch-1.0.json#/properties/calibration/properties/'+k) for k in ('source_position_m','effective_speed_m_s','source_effective_speed_covariance')})
props['calibration_id']={'type':'string','pattern':'^calibration-[a-f0-9]{20}$'};props['uncertainty']=text
required=['schema_version','status','physical_validation','calibration_input','recording_inputs','input_id','input_result_id','provenance','reference_geometry','training_capture_ids','validation_capture_ids','diagnostics','clock_interpretation','conditional_on']
result=obj(props,required)
result.update({'$schema':'https://json-schema.org/draft/2020-12/schema','$id':base+'calibration-result-1.1.json','title':'EchoSight inspectable reference calibration result v1.1','description':'Original recordings plus explicitly supplied reference geometry. Structural contract; PSD, matched identities, canonical hashes and acceptance remain runtime checks. No physical validation.'})
result['allOf']=[{'if':{'properties':{'status':{'const':'calibration_proposal'}}},'then':{'required':['calibration','calibration_id','uncertainty','acceptance','evidence','information_singular_values','training_normalized_rms','validation_normalized_rms','validation_max_abs_z','validation_nominal_rms_s','validation_fitted_rms_s','validation_max_abs_residual_s'],'properties':{'input_result_id':{'type':'string'},'recording_inputs':{'items':{'properties':{'hash_status':{'const':'verified'}}}}}},'else':{'not':{'anyOf':[{'required':['calibration']},{'required':['calibration_id']}]}}}]
(R/'schemas/calibration-result.schema.json').write_text(json.dumps(result,indent=2)+'\n')
