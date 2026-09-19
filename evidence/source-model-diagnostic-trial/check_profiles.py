from pathlib import Path
import sys,json,numpy as np
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import diagnostic as d
from diagnostic_v2 import profiles,DELAY_GRID
kernel=np.exp(-(d.TIME/.00004)**2);records=[]
for i in range(3):
 s=np.array([0.,0.,0.]);r=np.array([1.,0.,0.]);y=(1+i*.1)*kernel-.3*np.interp(d.TIME-14/48000,d.TIME,kernel,left=0,right=0);records.append(dict(source=s,receiver=r,y=y))
s,r,table,null=profiles(records,kernel);index=np.argmin(abs(DELAY_GRID-14/48000));p=[-343.*14/48000,0.,0.,0.];res,_,_=d.residual_profiles(p,'secondary',records,kernel,np.zeros(3),343.);error=float(np.max(abs(np.mean(res**2,axis=1)-table[:,index])));assert error<1e-14
(HERE/'profile-checks.json').write_text(json.dumps(dict(passed=True,table_full_objective_max_error=error,no_truth_labels_used=True),indent=2)+'\n');print(error)
