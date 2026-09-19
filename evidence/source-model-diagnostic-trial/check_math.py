from pathlib import Path
import json,sys,numpy as np
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
from diagnostic import delays,residual_profiles,TIME
s=np.array([[1.,1.,1.],[1.1,1.,1.2]]);r=np.array([[2.,1.2,1.8],[1.8,2.,1.4]]);ref=np.mean(s,axis=0);normal=np.array([0.,0.,1.]);distance=.4;offset=2*(distance-normal@ref)*normal
pred,valid=delays(np.r_[offset,.6],'plane',s,r,ref,343.)
expected=[]
for a,b in zip(s,r):
 image=a+2*(distance-normal@a)*normal;fraction=(distance-normal@b)/(normal@(image-b));bounce=b+fraction*(image-b);expected.append((np.linalg.norm(a-bounce)+np.linalg.norm(b-bounce)-np.linalg.norm(a-b))/343.+.00006)
assert valid and np.max(abs(pred-expected))<1e-14
kernel=np.exp(-(TIME/.00004)**2);delta=np.array([.2,.1,-.05]);params=np.r_[delta,.6];d,_=delays(params,'secondary',s,r,ref,343.);records=[]
for i in range(2):
 shift=1/48000;y=1.1*np.interp(TIME-shift,TIME,kernel,left=0,right=0)-.3*np.interp(TIME-shift-d[i],TIME,kernel,left=0,right=0);records.append(dict(source=s[i],receiver=r[i],y=y))
res,gain,alignment=residual_profiles(params,'secondary',records,kernel,ref,343.);assert np.max(abs(res))<1e-12 and np.max(abs(gain-[1.1,-.3]))<1e-12 and np.max(abs(alignment-1/48000))<1e-14
result=dict(passed=True,plane_broken_path_max_error_s=float(np.max(abs(pred-expected))),signed_gain_mixture_residual=float(np.max(abs(res))),alignment_moves_whole_mixture=True,no_recording_cases_generated=True)
(HERE/'math-checks.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
