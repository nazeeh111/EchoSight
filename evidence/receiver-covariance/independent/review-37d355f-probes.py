from pathlib import Path
import sys,json,copy
root=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(root/'work/review-37d355f-snapshot'))
import numpy as np
from scipy.spatial.transform import Rotation
from scipy.optimize import least_squares
from scipy.linalg import solve_triangular
from echosight import multisource as ms,path_alternatives as pa
from echosight import receiver_covariance as rc
from tests.test_multisource import fixture
from tests.test_receiver_covariance import declaration
rng=np.random.default_rng(993827)
data,bundle=fixture(receivers=4);rotation=Rotation.from_rotvec([.3,-.4,.2]).as_matrix();shift=np.array([5.,-3.,2.])
for item in data:
    item['session']['source_position_m']=(rotation@item['session']['source_position_m']+shift).tolist()
    for o in item['observations']:o['receiver_position_m']=(rotation@o['receiver_position_m']+shift).tolist()
v=343.;sources=np.array([p['session']['source_position_m'] for p in data for o in p['observations']]);r=np.array([o['receiver_position_m'] for p in data for o in p['observations']]);ref=sources[0]
rows=[dict(source_index=a,receiver_group=o['receiver_pose_group_id'],o=o,peaks=o['candidates'],t=np.array([p['delay_s'] for p in o['candidates']])) for a,item in enumerate(data) for o in item['observations']]
# Dense anisotropic PSD with negative as well as positive cross-capsule entries.
B=rng.normal(size=(12,7));R=B@B.T*2e-6+np.eye(12)*1e-7
decl=declaration(data,R);bundle['shared_calibration']['receiver_pose_covariance']=decl;cal=rc.validate(bundle,data)
n=rotation[:,0];ds=[float(n@shift),float(n@shift+4.5)];qs=[ref+2*(d-n@ref)*n for d in ds]
links=[(k,i,k) for i in range(16) for k in range(2)]
actual,rank,chi=ms._covariance(qs,ref,sources,r,v,rows,links,np.zeros((13,13)),cal)
J=np.zeros((32,6));D=np.zeros((32,12))
for j,(k,i,_) in enumerate(links):
    for axis in range(3):
        h=np.eye(3)[axis]*1e-5
        J[j,3*k+axis]=(ms._predict(qs[k]+h,ref,sources[i:i+1],r[i:i+1],v)[0][0]-ms._predict(qs[k]-h,ref,sources[i:i+1],r[i:i+1],v)[0][0])/2e-5
        group=int(rows[i]['receiver_group'][1:])
        D[j,3*group+axis]=(ms._predict(qs[k],ref,sources[i:i+1],r[i:i+1]+h,v)[0][0]-ms._predict(qs[k],ref,sources[i:i+1],r[i:i+1]-h,v)[0][0])/2e-5
noise=np.eye(32)*(2e-5)**2
for a,(_,i,_) in enumerate(links):
    for b,(_,j,_) in enumerate(links):
        if i==j:noise[a,b]+=(2e-5)**2
C=D@R@D.T+noise;L=np.linalg.pinv(J);expected=L@C@L.T
np.testing.assert_allclose(actual,expected,rtol=2e-8,atol=1e-13)
# Reorder the supplied covariance blocks without changing physical meaning.
order=[2,0,3,1];indices=np.concatenate([np.arange(3*k,3*k+3) for k in order]);permuted=copy.deepcopy(bundle)
permuted['shared_calibration']['receiver_pose_covariance']['group_ids']=[f'r{k}' for k in order]
permuted['shared_calibration']['receiver_pose_covariance']['covariance_m2']=R[np.ix_(indices,indices)].tolist()
pcal=rc.validate(permuted,data)
np.testing.assert_allclose(ms._covariance(qs,ref,sources,r,v,rows,links,np.zeros((13,13)),pcal)[0],actual,atol=1e-15)
# Compact point derivatives, nuisance covariance, and actual fixed-weight refits.
support=[dict(session_id=item['session']['session_id'],capture_id=o['capture_id'],candidate_id=o['candidates'][0]['candidate_id']) for item in data for o in item['observations']]
surface=dict(normal=n.tolist(),offset_m=ds[0],support=support)
prows,s,r,y,v,fixed,_,_=pa._evidence(surface,data,v,np.zeros((13,13)),cal)
p=rotation@np.array([2.3,2.,1.8])+shift
num=np.zeros((16,12));g=np.zeros((16,3));hsize=1e-5
for axis in range(3):
    h=np.eye(3)[axis]*hsize;g[:,axis]=(pa.prediction(p,s,r+h,v)-pa.prediction(p,s,r-h,v))/(2*hsize)
for i,row in enumerate(prows):
    k=int(row['group'][1:]);num[i,3*k:3*k+3]=g[i]
np.testing.assert_allclose(g,pa.derivatives(p,s,r,v)[2],rtol=1e-7,atol=1e-13)
pointC=num@R@num.T+np.eye(16)*2*(2e-5)**2
np.testing.assert_allclose(pa._point_nuisance_covariance(p,prows,s,r,v,np.zeros((13,13)),cal),pointC,rtol=1e-8,atol=1e-17)
Jp=pa.derivatives(p,s,r,v)[0];W=np.linalg.inv(fixed);Lp=np.linalg.solve(Jp.T@W@Jp,Jp.T@W)
expectedp=Lp@pointC@Lp.T;predictedp=pa._fixed_weight_covariance(Jp,fixed,pointC)
np.testing.assert_allclose(predictedp,expectedp,rtol=1e-10)
chol=np.linalg.cholesky(fixed);fits=[]
for _ in range(350):
    delta=rng.multivariate_normal(np.zeros(12),R).reshape(4,3)
    y=pa.prediction(p,s,r+np.tile(delta,(4,1)),v)+rng.normal(0,np.sqrt(2)*2e-5,16)
    fit=least_squares(lambda x:solve_triangular(chol,pa.prediction(x,s,r,v)-y,lower=True),p,jac=lambda x:solve_triangular(chol,pa.derivatives(x,s,r,v)[0],lower=True),max_nfev=25)
    assert fit.success;fits.append(fit.x)
empirical=np.cov(fits,rowvar=False);relative=np.linalg.norm(empirical-predictedp)/np.linalg.norm(predictedp)
assert relative<.2,relative
# Common-mode cancellation contrast: offdiagonal terms must reduce this variance to zero.
shared=dict(index={'a':0,'b':1},covariance=np.kron(np.ones((2,2)),np.eye(3)*.02**2))
projected=rc.project(['a','b'],[[1.,0,0],[1.,0,0]],[10.,10.],shared)
contrast=np.array([1.,-1.]);assert float(contrast@projected@contrast)==0
summary=dict(commit='37d355f786e1fa337a0f50f1fda4d6eb3c5eb0f9',tilted_two_plane_rank=int(rank),plane_covariance_relative_error=float(np.linalg.norm(actual-expected)/np.linalg.norm(expected)),plane_cross_block_norm=float(np.linalg.norm(actual[:3,3:])),group_order_invariant=True,point_receiver_derivative_max_abs_error=float(np.max(abs(g-pa.derivatives(p,s,r,v)[2]))),point_nonlinear_refits=350,point_refit_covariance_relative_error=float(relative),common_translation_contrast_variance=0.)
(root/'work/review-37d355f-probes.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
