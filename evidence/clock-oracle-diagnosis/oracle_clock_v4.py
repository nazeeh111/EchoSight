"""Postfreeze evaluation-oracle retry diagnosis; no mapping/refit or production edit."""
from pathlib import Path
import json,hashlib,types,sys
import numpy as np
P=Path(__file__).resolve().parent;CORE=P/'run-v4/checkouts/de8442b2dd088c036d2b92eaeaf29a1273785795';sys.path.insert(0,str(CORE))
from echosight.signals import process_recording
from echosight.storage import read_recording
source=(CORE/'echosight/signals.py').read_text()
# Only force the existing bounded retry and supply true rate to its template.
# Its nearest-pilot selection, improvement acceptance, refit, rejection and
# complete waveform re-extraction remain the exact immutable algorithm.
changed=source.replace("if np.max(np.abs(residual))>max(2/fs,.00010) and abs(alpha-1)<=.005:","if abs(alpha-1)<=.005:",1).replace("np.arange(round(p['duration_s']*fs*alpha))/(fs*alpha)","np.arange(round(p['duration_s']*fs*ORACLE_ALPHA))/(fs*ORACLE_ALPHA)",1)
assert changed!=source
rows=[]
for family in ['direct_null','single_room','near_reflector']:
 folder=P/'run-v4/fresh'/f'{family}-2459';saved=json.loads((folder/'baseline.json').read_text())['result'];item=saved['processed_sessions'][2];session=item['session'];old=item['observations'][1];truth=json.loads((folder/'truth.json').read_text())['sessions'][2]['captures'][1]
 raw=folder/'source-02/capture-01.wav';samples,rate=read_recording(raw)
 reproduced=process_recording(samples,rate,session['probe'],'capture-01');assert reproduced['clock']==old['clock'];assert reproduced['candidates']==old['candidates']
 module=types.ModuleType('evaluation_oracle_signals');module.__dict__['ORACLE_ALPHA']=truth['alpha'];exec(compile(changed,'evaluation_oracle_signals','exec'),module.__dict__)
 new=module.process_recording(samples,rate,session['probe'],'capture-01')
 def describe(o):
  result=dict(status=o['status'],clock=o['clock'],rate_error_ppm=(o['clock']['alpha']-truth['alpha'])*1e6,rate_standardized_error=(o['clock']['alpha']-truth['alpha'])/o['clock']['alpha_std'],direct_std_s=o.get('direct_std_s'),candidate_count=len(o['candidates']),diagnostics=o['diagnostics'])
  if o['status']!='ok':return result
  response=o['response'];y=np.array(response['values']);axis=response['start_delay_s']+np.arange(len(y))/response['sample_rate_hz'];result['direct_response_amplitude']=o['quality']['direct_response_amplitude'];result['noise_response_amplitude']=o['quality']['noise_response_amplitude'];result['normalizer_at_zero']=float(np.interp(0,axis,y));result['geometric_excess_timing_errors']=[]
  direct=next(p['delay_s'] for p in truth['paths'] if p['kind']=='direct-emitter-0')
  for p in truth['paths']:
   if p['kind']=='direct-emitter-0':continue
   actual=p['delay_s']-direct;candidates=o['candidates'];nearest=min(candidates,key=lambda c:abs(c['delay_s']-actual)) if candidates else None
   result['geometric_excess_timing_errors'].append(dict(path_kind=p['kind'],actual_excess_s=actual,nearest_candidate_id=nearest['candidate_id'] if nearest else None,error_s=nearest['delay_s']-actual if nearest else None,path_error_m=(nearest['delay_s']-actual)*(343.45/1.00035) if nearest else None,conditional_standardized_error=(nearest['delay_s']-actual)/np.sqrt(nearest['delay_std_s']**2+o['direct_std_s']**2+(actual*o['clock']['alpha_std']/o['clock']['alpha'])**2) if nearest else None,semantics='Evaluation nearest compatibility only; no labels supplied to extraction, no one-to-one association claim'))
  return result
 rows.append(dict(family=family,seed=2459,source_index=2,capture_id='capture-01',raw_sha256=hashlib.sha256(raw.read_bytes()).hexdigest(),actual_alpha=truth['alpha'],original=describe(old),oracle_template_retry=describe(new)))
result=dict(core_signals_sha256=hashlib.sha256(source.encode()).hexdigest(),oracle_code_sha256=hashlib.sha256(changed.encode()).hexdigest(),true_clock_convention='raw y(t_receiver)=x((t_receiver-offset)/alpha); alpha includes receiver relative to source-buffer seconds, so equal to fitted alpha target',scope='Evaluation-only true-rate template diagnosis on three exposed development cases. No new mapping/guard runs, no production/source-prototype changes, no operational recommendation.',cases=rows)
(P/'v4-oracle-clock-results.json').write_text(json.dumps(result,indent=2)+'\n')
for r in rows:print(r['family'],[(k,r[k]['status'],r[k]['rate_error_ppm'],r[k]['rate_standardized_error'],r[k].get('direct_response_amplitude'),r[k].get('noise_response_amplitude')) for k in ['original','oracle_template_retry']])
