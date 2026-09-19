from pathlib import Path
import time
import numpy as np
from scipy.optimize import least_squares
from scipy.stats import qmc
import diagnostic as base
DELAY_GRID=np.arange(-96,97)/48000
SOBOL=qmc.Sobol(4,scramble=False).random_base2(12)
CACHE={}

def profiles(records,kernel):
 key=(id(records),id(kernel))
 if key in CACHE:return CACHE[key]
 s,r,y=base.arrays(records);costs=[]
 # Use an algebraic primary+shifted-kernel mixture for each proposed delay.
 for delay in DELAY_GRID:
  best=np.full(len(y),np.inf)
  for shift in base.SHIFTS:
   a=np.interp(base.TIME-shift,base.TIME,kernel,left=0,right=0);b=np.interp(base.TIME-shift-delay,base.TIME,kernel,left=0,right=0);aa=a@a;bb=b@b;ab=a@b;ay=y@a;by=y@b;det=aa*bb-ab**2
   if det>1e-9:ga=(ay*bb-by*ab)/det;gb=(by*aa-ay*ab)/det
   else:ga=ay/max(aa,1e-15);gb=np.zeros(len(y))
   ga=np.clip(ga,0,2);gb=np.clip(gb,-2,2);res=y-ga[:,None]*a-gb[:,None]*b;best=np.minimum(best,np.mean(res**2,axis=1))
  costs.append(best)
 table=np.array(costs).T;single=base.residual_profiles([],'single',records,kernel,np.mean(s,axis=0),343.)[0];null=np.mean(single**2,axis=1);CACHE.clear();CACHE[key]=(s,r,table,null);return CACHE[key]

ORIGINAL_FIT=base.fit

def fit(model,records,kernel,reference,v):
 if model=='single':return ORIGINAL_FIT(model,records,kernel,reference,v)
 start=time.perf_counter();s,r,table,null=profiles(records,kernel);bound=.45 if model=='secondary' else 2.;lower=np.r_[[-bound]*3,-1.5];upper=-lower
 def objective(p):
  d,valid=base.delays(p,model,s,r,reference,v)
  if not valid:return np.ones(len(records))*5
  return np.sqrt(np.maximum([np.interp(x,DELAY_GRID,row,left=z,right=z) for x,row,z in zip(d,table,null)],0))
 points=lower+(upper-lower)*SOBOL;coarse=np.array([np.mean(objective(p)**2) for p in points]);selected=np.argsort(coarse)[:20];answers=[];count=0
 for index in selected:
  opt=least_squares(objective,points[index],bounds=(lower,upper),max_nfev=70,diff_step=1e-4,ftol=1e-7,xtol=1e-7,gtol=1e-7);count+=opt.nfev;answers.append((float(np.mean(opt.fun**2)),opt.x))
 answers.sort(key=lambda x:x[0]);refined=[]
 for cost,p in answers:
  if any(np.linalg.norm(p-q)<.01 for q in refined):continue
  refined.append(p)
  if len(refined)==3:break
 final=[]
 for p in refined:
  raw=lambda x:base.residual_profiles(x,model,records,kernel,reference,v)[0].ravel()
  opt=least_squares(raw,p,bounds=(lower,upper),max_nfev=70,diff_step=1e-4,ftol=1e-7,xtol=1e-7,gtol=1e-7);count+=opt.nfev;final.append((float(np.mean(opt.fun**2)),opt))
 cost,opt=min(final,key=lambda x:x[0]);boundary=bool(np.any(np.abs(opt.x[:3])>bound-.002) or abs(opt.x[3])>1.49)
 return dict(model=model,parameters=opt.x.tolist(),training_mse=cost,runtime_s=time.perf_counter()-start,search_boundary=boundary,evaluations=count,coarse_evaluations=len(points),coarse_min_training_mse=float(min(coarse)),profile_refined_min_training_mse=answers[0][0],profile_refinement_starts=20,raw_refinement_starts=len(refined),optimizer_success=bool(opt.success))

def diagnose(result,v=343.):
 CACHE.clear();base.fit=fit
 try:return base.diagnose(result,v)
 finally:base.fit=ORIGINAL_FIT
