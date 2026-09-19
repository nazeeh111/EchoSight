import inspect,ast,copy,hashlib,importlib.util,json,sys,time,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
CANDIDATE=ROOT/'work/spatial-finish/experimental_multisource_v2.py'
spec=importlib.util.spec_from_file_location('echosight.multisource',CANDIDATE);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
import echosight
sys.modules['echosight.multisource']=m;echosight.multisource=m
out={"candidate_sha256":hashlib.sha256(CANDIDATE.read_bytes()).hexdigest()}
fixture=json.loads((ROOT/'work/spatial-finish/fixtures/higher-order-1129-observations.json').read_text())
# Observe the real fit's covariance and downstream interpretation arguments.
observed={};orig_cov=m._covariance;orig_parent=m._parent_subset_alternatives

def cov(qs,reference,sources,receivers,v,rows,links,*args):
    assert m._supported(links,rows,len(qs))
    assert len(set((i,l) for k,i,l in links))==len(links)
    assert set(k for k,i,l in links)==set(range(len(qs)))
    score,assigned=m._assign(qs,reference,sources,receivers,v,rows)
    assert assigned==links
    c,rank,chi=orig_cov(qs,reference,sources,receivers,v,rows,links,*args)
    assert c.shape==(3*len(qs),3*len(qs));assert np.isfinite(c).all()
    assert np.allclose(c,c.T);assert np.linalg.eigvalsh(c).min()>-1e-10
    observed.update(qs=copy.deepcopy(qs),links=copy.deepcopy(links),cov=c.copy(),rank=rank,score=score)
    return c,rank,chi

def parent(out,qs,reference,sources,receivers,v,rows,links,calcov,pcov,*args):
    assert np.array_equal(qs,observed['qs']);assert links==observed['links'];assert np.array_equal(pcov,observed['cov'])
    observed['parent_checked']=True
    return orig_parent(out,qs,reference,sources,receivers,v,rows,links,calcov,pcov,*args)

before=json.dumps(fixture,sort_keys=True)
with patch.object(m,'_covariance',side_effect=cov),patch.object(m,'_parent_subset_alternatives',side_effect=parent):
    t=time.perf_counter();result=m.infer_scene_bundle(fixture['processed_sessions'],fixture['bundle']);elapsed=time.perf_counter()-t
assert json.dumps(fixture,sort_keys=True)==before
assert observed['parent_checked'];assert observed['rank']==3*len(observed['qs'])
assert observed['score']<0;assert len(result['surfaces'])==6
out['real_fixture']={"status":result['status'],"surfaces":len(result['surfaces']),"diagnostics":result['diagnostics'],"fit_planes":len(observed['qs']),"links":len(observed['links']),"rank":int(observed['rank']),"minimum_covariance_eigenvalue":float(np.linalg.eigvalsh(observed['cov']).min()),"score":observed['score'],"seconds":elapsed}
# Trigger cancellation only once the real pruning pass has reduced model size.
orig_assign=m._assign;state={'previous':None,'cancel':False,'calls':0}

def cancelling_assign(qs,*args):
    answer=orig_assign(qs,*args)
    if any(f.frame.f_code.co_name=='infer_scene_bundle' and f.frame.f_locals.get('pruned',0)>0 for f in inspect.stack()):state['cancel']=True
    state['previous']=len(qs);state['calls']+=1
    return answer
with patch.object(m,'_assign',side_effect=cancelling_assign):
    result=m.infer_scene_bundle(fixture['processed_sessions'],fixture['bundle'],cancel=lambda:state['cancel'])
assert state['cancel'];assert result['status']=='cancelled';assert not result['surfaces'] and not result['hypotheses']
assert 'shared_plane_parameter_covariance_m2' not in result
out['cancel_after_pruning']={'status':result['status'],'assign_calls':state['calls'],'geometry_cleared':True}
# Execute the exact AST of the changed loop with controlled assignment/support
# outcomes to force boundary transitions not present in this fixture.
tree=ast.parse(CANDIDATE.read_text());fun=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='infer_scene_bundle')
tryblock=next(n for n in fun.body if isinstance(n,ast.Try));loop=next(n for n in tryblock.body if isinstance(n,ast.While))
source=ast.unparse(loop)
compiled=compile(ast.Module(body=[loop],type_ignores=[]),str(CANDIDATE),'exec')
scenarios={}
for scenario in ('cascade','all_removed','empty_assignment'):
    trace=[];fitcalls=[];supportcalls=[]
    def assign(qs,*args):
        trace.append([int(q[0]) for q in qs])
        return 0,([] if scenario=='empty_assignment' else [(k,k,0) for k in range(len(qs))])
    def supported(links,rows,count):
        supportcalls.append(links)
        if scenario!='cascade':return False
        return links[0][1]>0 if len(trace[-1])>1 else True
    def least(fun,q,max_nfev):
        fitcalls.append(int(q[0]));return type('Fit',(),{'x':q})()
    env={**m.__dict__,'qs':[np.array([i,0.,0.]) for i in range(10)],'pruned':0,'cancel':None,'reference':np.zeros(3),'sources':np.zeros((10,3)),'receivers':np.zeros((10,3)),'v':343.,'allrows':[{'t':np.array([0.])} for _ in range(10)],'_assign':assign,'_supported':supported,'least_squares':least}
    exec(compiled,env)
    expected=1 if scenario=='cascade' else 0
    assert len(env['qs'])==expected
    if scenario=='cascade':assert env['pruned']==9 and len(trace)==30 and len(fitcalls)==110
    if scenario=='empty_assignment':assert not fitcalls
    scenarios[scenario]={'pruned':env['pruned'],'remaining':len(env['qs']),'assignment_calls':len(trace),'fit_calls':len(fitcalls)}
out['boundary_loop']=scenarios
(ROOT/'work/review-spatial-pruning/probe-results.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
