from pathlib import Path
import json
import numpy as np
from scipy.optimize import least_squares,brentq
ROOT=Path(__file__).resolve().parent;rng=np.random.default_rng(27119);v=343.;n=np.array([1.,0.,0.]);d=.2
r0=rng.uniform([-2.,-1.3,.3],[-.35,1.2,2.2],(12,3));sources=np.array([[0,0,1.2],[.006,.45,1.6],[-.005,-.4,1.35],[.003,.15,.7]])
s=np.repeat(sources,12,0);r=np.tile(r0,(4,1));ids=np.repeat(np.arange(4),12);q=s+2*(d-s@n)[:,None]*n
y=(np.linalg.norm(q-r,axis=1)-np.linalg.norm(s-r,axis=1))/v
# This intentionally grants one driver delay per source, violating configuration stability.
def model(x):return (np.linalg.norm(s+x[:3]-r,axis=1)-np.linalg.norm(s-r,axis=1))/v+x[3:][ids]*1e-3
fit=least_squares(lambda x:(model(x)-y)*1e6,np.r_[[.4,0,0],[0.]*4],bounds=(np.r_[[-1]*3,[-1.]*4],np.r_[[1]*3,[1.]*4]),max_nfev=500,ftol=1e-12,xtol=1e-12,gtol=1e-10)
e=model(fit.x)-y
# Six noncoplanar receivers on a distance-difference locus defeat the generic
# position-plus-common-delay uniqueness condition, despite receiver rank three.
a=np.array([.4,0,1.2]);b=np.array([.46,0,1.2]);distance_difference=-.04
rr=[]
for yy,zz in [(-1,.3),(.8,.5),(-.4,2.2),(1.2,1.8),(.3,1.1),(-1.4,1.5)]:
 xx=brentq(lambda xx:np.linalg.norm(np.array([xx,yy,zz])-a)-np.linalg.norm(np.array([xx,yy,zz])-b)-distance_difference,-100,100)
 rr.append([xx,yy,zz])
rr=np.array(rr);ranges=np.linalg.norm(rr-a,axis=1);A=np.column_stack([2*(rr[1:]-rr[0]),-2*(ranges[1:]-ranges[0])])
report={'source_specific_driver_delay':{'source_rank':3,'rms_difference_us':float(np.sqrt(np.mean(e**2))*1e6),'max_difference_us':float(max(abs(e))*1e6),'fitted_offsets_us':(fit.x[3:]*1e3).tolist(),'delay_bound_us':1000,'semantics':'additional nuisance freedom only; not authorized constant-driver assumption'},'nongeneric_receiver_alias':{'receiver_count':6,'all_receivers_same_side_of_candidate_plane_as_source':bool(np.all(rr[:,0]<.2)),'receiver_rank':int(np.linalg.matrix_rank(rr-rr.mean(0))),'position_plus_delay_equations_rank':int(np.linalg.matrix_rank(A,tol=1e-9)),'receiver_positions_m':rr.tolist(),'virtual_positions_m':[a.tolist(),b.tolist()],'compensating_driver_delay_us':distance_difference/v*1e6,'max_distance_difference_error_m':float(max(abs(np.linalg.norm(rr-a,axis=1)-np.linalg.norm(rr-b,axis=1)-distance_difference)))}}
(ROOT/'nuisance-results.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
