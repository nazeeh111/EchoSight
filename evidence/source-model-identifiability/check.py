from pathlib import Path
import json
import numpy as np
from scipy.optimize import least_squares
from scipy.linalg import solve_triangular
ROOT=Path(__file__).resolve().parent
rng=np.random.default_rng(27119);v=343.;n=np.array([1.,0.,0.]);d=.2
receiver=rng.uniform([-2.,-1.3,.3],[-.35,1.2,2.2],(12,3))
layouts={
 'one_source':[[0,0,1.2]],
 'two_tangential':[[0,0,1.2],[0,.6,1.5]],
 'two_normal':[[0,0,1.2],[.1,0,1.2]],
 'line_tangential':[[0,y,1.2] for y in [-.6,-.2,.2,.6]],
 'line_normal':[[x,0,1.2] for x in [-.1,-.03,.03,.1]],
 'coplanar_tangential':[[0,-.4,.8],[0,.4,.8],[0,-.4,1.6],[0,.4,1.6]],
 'coplanar_with_normal_motion':[[-.08,-.4,1.2],[.08,-.4,1.2],[-.08,.4,1.2],[.08,.4,1.2]],
 'four_3d':[[0,0,1.2],[.1,.45,1.6],[-.08,-.4,1.35],[.06,.15,.7]],
 'four_3d_short_normal':[[0,0,1.2],[.006,.45,1.6],[-.005,-.4,1.35],[.003,.15,.7]],
}
def plane(s,r):
 q=s+2*(d-s@n)[:,None]*n
 return (np.linalg.norm(q-r,axis=1)-np.linalg.norm(s-r,axis=1))/v

def emitter(s,r,delta,tau):return (np.linalg.norm(s+delta-r,axis=1)-np.linalg.norm(s-r,axis=1))/v+tau

def covariance(src,s,r):
 count=len(src);nr=len(receiver);mu=plane(s,r);q=s+2*(d-s@n)[:,None]*n
 u=(q-r)/np.linalg.norm(q-r,axis=1)[:,None];u0=(s-r)/np.linalg.norm(s-r,axis=1)[:,None]
 Js=(u@(np.eye(3)-2*np.outer(n,n))-u0)/v;Jr=(u0-u)/v
 G=np.zeros((len(s),3*count+3*nr+1));S=np.zeros((G.shape[1],G.shape[1]));common=np.tile(np.eye(3),(count,1))
 S[:3*count,:3*count]=common@common.T*.003**2+np.eye(3*count)*.004**2
 S[3*count:3*count+3*nr,3*count:3*count+3*nr]=np.eye(3*nr)*.006**2;S[-1,-1]=.6**2
 for i in range(len(s)):
  G[i,3*(i//nr):3*(i//nr)+3]=Js[i];G[i,3*count+3*(i%nr):3*count+3*(i%nr)+3]=Jr[i];G[i,-1]=-mu[i]/v
 return G@S@G.T+np.eye(len(s))*(20e-6)**2
reports={}
for name,poses in layouts.items():
 src=np.array(poses,float);s=np.repeat(src,12,axis=0);r=np.tile(receiver,(len(src),1));y=plane(s,r);C=covariance(src,s,r);L=np.linalg.cholesky(C)
 def resid(x):return solve_triangular(L,emitter(s,r,x[:3],x[3]*1e-3)-y,lower=True)
 starts=[[.4,0,0,0],[.3,.1,.1,.1],[.5,-.1,-.1,-.1]]
 fits=[least_squares(resid,x,bounds=([-1,-1,-1,-.15],[1,1,1,.15]),max_nfev=300,gtol=1e-11,xtol=1e-11,ftol=1e-11) for x in starts]
 fit=min(fits,key=lambda f:f.fun@f.fun);delta=fit.x[:3];tau=fit.x[3]*1e-3;error=emitter(s,r,delta,tau)-y
 profiled=np.maximum(abs(error)-2/48000,0.)
 reports[name]=dict(source_rank=int(np.linalg.matrix_rank(src-src.mean(0),tol=1e-9)),source_normal_span_m=float(np.ptp(src@n)),profiled_offset_m=delta.tolist(),profiled_driver_delay_us=float(tau*1e6),rms_model_difference_us=float(np.sqrt(np.mean(error**2))*1e6),max_model_difference_us=float(max(abs(error))*1e6),fixed_plane_covariance_score=float(fit.fun@fit.fun),rms_after_independent_two_sample_echo_shift_us=float(np.sqrt(np.mean(profiled**2))*1e6))
# Genuine full-3D two-sided degeneracy with unknown orientation and fixed baseline length.
ss=np.array([[.2,0,.8],[-.2,.5,1.],[.2,.7,1.8],[-.2,-.4,1.6]])
rr=np.repeat(ss,4,axis=0)+np.tile(np.array([[.4,.1,.1],[.5,-.1,.2],[.6,.2,-.2],[.7,-.3,.3]]),(4,1))
for i in range(len(rr)):
 if ss[i//4,0]<0:rr[i,0]=ss[i//4,0]-(rr[i,0]-ss[i//4,0])
s=np.repeat(ss,4,axis=0);q=s.copy();q[:,0]*=-1
relative_offsets=q-s;excess=(np.linalg.norm(q-rr,axis=1)-np.linalg.norm(s-rr,axis=1))/v
orientation_alias=dict(source_rank=int(np.linalg.matrix_rank(ss-ss.mean(0))),baseline_norms_m=np.unique(np.round(np.linalg.norm(relative_offsets,axis=1),8)).tolist(),every_plane_path_same_halfspace=bool(np.all(s[:,0]*rr[:,0]>0)),minimum_excess_delay_us=float(excess.min()*1e6),max_exact_alias_error_s=0.,required_orientation='secondary baseline alternates +x/-x; source acoustic reference at x=±0.2m')
# Freeze two explanations at the original same-x calibration view. Candidate
# source relocation prediction uses actual receiver range, not plane distance/2.
base=np.array([0.,0.,1.2]);candidates={'same_x_y_move':base+[0,.25,0],'same_x_z_move':base+[0,0,.25],'normal_toward_plane':base+[.1,0,0],'normal_away_plane':base+[-.1,0,0]}
guidance={}
for name,sp in candidates.items():
 s=np.tile(sp,(12,1));ep=plane(s,receiver);es=emitter(s,receiver,np.array([.4,0,0]),0.);diff=ep-es
 guidance[name]=dict(source_position_m=sp.tolist(),rms_predicted_separation_us=float(np.sqrt(np.mean(diff**2))*1e6),min_predicted_separation_us=float(min(abs(diff))*1e6),receiver_positions_m=receiver.tolist())
report=dict(seed=27119,conventions={'effective_speed_m_s':v,'driver_delay_profile_bound_us':150,'independent_timing_std_us':20,'shared_source_center_std_m':.003,'per_source_placement_std_m':.004,'reused_receiver_std_m':.006,'shared_effective_speed_std_m_s':.6},layouts=reports,unknown_orientation_exact_alias=orientation_alias,next_measurement=guidance,limitations='analytic identifiability and chosen uncertainty budget only; not waveform detector or calibrated false-alarm evaluation')
(ROOT/'results.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='next_measurement'},indent=2))
