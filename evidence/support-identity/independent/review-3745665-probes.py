"""Run from backend with its .venv; only immutable snapshot code is imported."""
import copy, hashlib, importlib.util, json, pathlib, subprocess, sys, tempfile
from jsonschema import Draft202012Validator
ROOT=pathlib.Path(__file__).resolve().parents[1]
SNAP=ROOT/'work/review-3745665-snapshot'
sys.path.insert(0,str(SNAP))
from echosight.evolution import compare_results
V=Draft202012Validator(json.loads((SNAP/'schemas/comparison.schema.json').read_text()))
def result(revision,scope='A',ids=('0','1')):
    return dict(schema_version='1.0',result_id=revision,session_id=scope,status='partial',
       acquisition=dict(coordinate_frame_id='survey',source_position_m=[0.,0.,0.],sound_speed_m_s=343.,source_clock_scale=1.,probe={'probe_id':'probe'}),
       surfaces=[dict(surface_id='plane-'+revision,normal=[1.,0.,0.],offset_m=2.,support=[dict(capture_id=i,candidate_id='peak') for i in ids])],
       observations=[dict(capture_id=i) for i in ids])
checks=[]
def check(name,a,b,expected,carry=None):
    before=copy.deepcopy((a,b,carry));out=compare_results(a,b,previous_comparison=carry)
    assert (a,b,carry)==before,name+' mutation'
    V.validate(out)
    m=out['correspondences'][0]
    actual=(out['support_comparison_status'],m['additional_support_count'],out['new_capture_references'],m['lost_support_references'])
    assert actual==expected,(name,actual,expected)
    assert out['physical_scene_change_established'] is False
    checks.append({'name':name,'support_status':actual[0],'count':actual[1],'new':actual[2],'lost':actual[3]})
    return out
refs=lambda s,ids:[dict(session_id=s,capture_id=i) for i in ids]
a,b=result('a'),result('b','B')
ab=check('cross-session local-name reuse',a,b,('available',2,refs('B',['0','1']),refs('A',['0','1'])))
check('same-session reprocessing',a,result('z'),('available',0,[],[]))
check('same-session append',a,result('z',ids=('0','1','2')),('available',1,refs('A',['2']),[]))
for where in ('previous','current','both'):
    left,right=copy.deepcopy(a),copy.deepcopy(b)
    if where in ('previous','both'):left.pop('session_id')
    if where in ('current','both'):right.pop('session_id')
    check('missing '+where,left,right,('unavailable',None,[],[]))
for top in ('absent','null','matching'):
    nested=result('nested','A');nested['acquisition']['session_id']='A'
    if top=='absent':nested.pop('session_id')
    if top=='null':nested['session_id']=None
    check('nested scope '+top,a,nested,('available',0,[],[]))
rejected=[]
for field in ('top','nested'):
    for value in ('',False,3,[],{},'s'*161):
        bad=result('bad');target=bad if field=='top' else bad['acquisition'];target['session_id']=value
        try:compare_results(a,bad)
        except ValueError:rejected.append(field+':'+repr(value)[:30])
        else:raise AssertionError('accepted invalid '+field+repr(value))
bad=result('bad');bad['acquisition']['session_id']='different'
try:compare_results(a,bad)
except ValueError:rejected.append('scope conflict')
else:raise AssertionError('scope conflict accepted')
for field in ('observations','support'):
    bad=result('bad');seq=bad['observations'] if field=='observations' else bad['surfaces'][0]['support'];seq.append(copy.deepcopy(seq[0]))
    try:compare_results(a,bad)
    except ValueError:rejected.append('duplicate '+field)
    else:raise AssertionError('duplicate accepted')
legacy=copy.deepcopy(ab);legacy['schema_version']='1.0'
for field in ('previous_session_id','current_session_id','support_comparison_status','new_capture_references'):legacy.pop(field)
for m in legacy['correspondences']:
    m.pop('additional_support_references');m.pop('lost_support_references')
V.validate(legacy)
c=result('c','B',('0','1','2'))
for name,carry in [('legacy',legacy),('new',ab)]:
    bc=check(name+' track carry',b,c,('available',1,refs('B',['2']),[]),carry)
    assert bc['current_tracks'][0]['track_id']=='plane-a'
    cd=check(name+' subsequent new carry',c,result('d','C'),('available',2,refs('C',['0','1']),refs('B',['0','1','2'])),bc)
    assert cd['current_tracks'][0]['track_id']=='plane-a'
# Load the exact previous implementation to reproduce the corrected behavior.
parent=subprocess.check_output(['git','rev-parse','0f05dd1'],cwd=ROOT,text=True).strip()
source=subprocess.check_output(['git','show',parent+':echosight/evolution.py'],cwd=ROOT)
parentpath=ROOT/'work/review-3745665-parent-evolution.py';parentpath.write_bytes(source)
spec=importlib.util.spec_from_file_location('prior_evolution',parentpath);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
old=module.compare_results(a,b)
assert old['correspondences'][0]['additional_support_count']==0 and old['new_capture_ids']==[]
# Real CLI old-state ingestion and preservation on a new scope contradiction.
with tempfile.TemporaryDirectory(dir=ROOT/'work') as tmp:
    tmp=pathlib.Path(tmp)
    for name,value in [('b',b),('c',c),('legacy',legacy)]: (tmp/(name+'.json')).write_text(json.dumps(value))
    dest=tmp/'output.json';cmd=[sys.executable,'-m','echosight','compare',str(tmp/'b.json'),str(tmp/'c.json'),'--previous-comparison',str(tmp/'legacy.json'),'--output',str(dest)]
    run=subprocess.run(cmd,cwd=SNAP,capture_output=True,text=True);assert run.returncode==0,run.stderr
    output=json.loads(dest.read_text());V.validate(output);assert output['schema_version']=='1.1';assert output['current_tracks'][0]['track_id']=='plane-a'
    saved=dest.read_bytes();c['acquisition']['session_id']='contradiction';(tmp/'c.json').write_text(json.dumps(c))
    failure=subprocess.run(cmd,cwd=SNAP,capture_output=True,text=True);assert failure.returncode!=0 and dest.read_bytes()==saved
report={'commit':'3745665352f59bc88e432b1f703054ab29398ce1','parent':parent,'checks':checks,'rejected_cases':rejected,'parent_cross_session_additional_count':0,'current_cross_session_additional_count':2,'cli_legacy_to_new_and_conflict_preservation':'passed','no_input_mutation':'all successful probe calls','scope':'declared result/acquisition session identity; no physical independence inference'}
files=['echosight/evolution.py','echosight/api.py','echosight/cli.py','schemas/comparison.schema.json','schemas/result.schema.json','docs/TRACKING.md','docs/FRONTEND_HANDOFF.md','docs/CHARTER.md','tests/test_evolution.py','tests/test_tracking_integration.py']
report['source_sha256']={p:hashlib.sha256((SNAP/p).read_bytes()).hexdigest() for p in files}
(ROOT/'work/review-3745665-probes.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'checks':len(checks),'rejections':len(rejected),'cli':'passed','parent_reproduction':'0 => 2 additional supports'},indent=2))
