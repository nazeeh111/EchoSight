from pathlib import Path
import json
import numpy as np
from scipy.optimize import lsq_linear
from gain_v4 import bounded_gains
rng=np.random.default_rng(94417);rows=[]
for kind in ['random','correlated','near_degenerate','identical','zero_primary','zero_secondary','both_zero','bound_primary','bound_secondary']:
 for i in range(40):
  a=rng.normal(size=107);b=rng.normal(size=107)
  if kind=='correlated':b=.98*a+.02*b
  if kind=='near_degenerate':b=a+1e-8*b
  if kind=='identical':b=a.copy()
  if kind in ['zero_primary','both_zero']:a*=0
  if kind in ['zero_secondary','both_zero']:b*=0
  gains=rng.uniform([-4,-5],[5,5]);y=gains[0]*a+gains[1]*b+rng.normal(0,.05,len(a))
  if kind=='bound_primary':y=3*a-.2*b
  if kind=='bound_secondary':y=.3*a+4*b
  pair,res=bounded_gains(a,b,y[None,:]);answer=lsq_linear(np.column_stack([a,b]),y,bounds=([0,-2],[2,2]),method='bvls',tol=1e-12,max_iter=1000)
  actual=float(res[0]@res[0]);reference=float(np.sum(answer.fun**2));error=actual-reference
  assert error<=1e-9*max(1.,reference),(kind,error,reference)
  assert np.all(pair[0]>=[0,-2]) and np.all(pair[0]<=[2,2])
  if kind=='zero_secondary':assert pair[0,1]==0
  rows.append(dict(kind=kind,cost=actual,reference_cost=reference,difference=error))
a=np.array([1.,0.]);b=np.array([.8,.6]);y=3*a-b;g,r=bounded_gains(a,b,y[None,:]);assert np.allclose(g[0],[2,-.2]);assert np.isclose(r[0]@r[0],.36)
result=dict(cases=len(rows),maximum_absolute_cost_difference=max(abs(r['difference']) for r in rows),algebraic_counterexample=dict(exact_gains=g[0].tolist(),exact_cost=float(r[0]@r[0]),old_clipped_cost=1.),all_passed=True,details=rows)
Path(__file__).with_name('v4-gain-checks.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='details'}))
