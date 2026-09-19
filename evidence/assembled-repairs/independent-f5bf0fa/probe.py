from pathlib import Path
import sys,copy,json,signal,contextlib,io
from unittest.mock import patch
P=Path(__file__).resolve().parent;S=P/'source';sys.path.insert(0,str(S))
from evaluation.controlled_development import recording_protocol
from echosight.pipeline import process_session,save_result
from echosight import controlled
from echosight.cli import main
protocol=recording_protocol(P/'raw','moved')
results=[process_session(e['session']) for e in protocol['epochs']]
assert all(r['surfaces'] for r in results)
report={'commit':'f5bf0fa412db9479779a7e944e14ea8c4ea983b7','raw_epoch_statuses':[r['status'] for r in results]}
original=controlled._spatial_changes
state={'cancelled':False}
def cancel_after_spatial(*a,**kw):
 value=original(*a,**kw);state['cancelled']=True;return value
with patch('echosight.pipeline.process_session',side_effect=copy.deepcopy(results)),patch('echosight.controlled._spatial_changes',side_effect=cancel_after_spatial):
 out=controlled.process_controlled_protocol(protocol,cancel=lambda:state['cancelled'])
report['core_late_cancel']={k:out[k] for k in ('status','conditional_spatial_changes','receiver_evidence')}
assert out['status']=='cancelled' and out['conditional_spatial_changes']
protocolpath=P/'protocol.json';save_result(protocol,protocolpath)
def interrupt_after_spatial(*a,**kw):
 value=original(*a,**kw);signal.raise_signal(signal.SIGINT);return value
with patch('echosight.pipeline.process_session',side_effect=copy.deepcopy(results)),patch('echosight.controlled._spatial_changes',side_effect=interrupt_after_spatial),contextlib.redirect_stdout(io.StringIO()):
 code=main(['controlled',str(protocolpath),'--output',str(P/'cli-cancelled.json')])
cli=json.loads((P/'cli-cancelled.json').read_text());report['cli']={'exit_code':code,'status':cli['status'],'conditional_spatial_changes':len(cli['conditional_spatial_changes']),'receiver_evidence':len(cli['receiver_evidence'])}
# Cancellation before receiver 2 should not publish partial positive evidence.
original_receiver=controlled._receiver_evidence;state={'cancelled':False}
def cancel_after_receiver(*a,**kw):
 value=original_receiver(*a,**kw);state['cancelled']=True;return value
with patch('echosight.pipeline.process_session',side_effect=copy.deepcopy(results)),patch('echosight.controlled._receiver_evidence',side_effect=cancel_after_receiver):
 early=controlled.process_controlled_protocol(protocol,cancel=lambda:state['cancelled'])
report['receiver_cancel']={'status':early['status'],'receiver_evidence':len(early['receiver_evidence']),'repeatable_change':early['receiver_evidence'][0]['repeatable_change']}
# Ordinary pipeline: callback at outer final completion is after inference's cancellation boundary.
state={'cancelled':False}
def final(f,m=''):
 if f==1 and m in ('ok','partial','ambiguous','no_result'):state['cancelled']=True
late=process_session(protocol['epochs'][0]['session'],cancel=lambda:state['cancelled'],progress=final)
report['outer_pipeline_callback']={'cancel_requested':state['cancelled'],'status':late['status'],'surfaces':len(late['surfaces'])}
(P/'probe-results.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='core_late_cancel'},indent=2));print('late controlled surfaces',len(out['conditional_spatial_changes']))
