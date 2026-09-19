"""Experimental equal-input source versus near-reflector waveform comparison."""
from pathlib import Path
import time
import numpy as np
from scipy.optimize import least_squares

RATE=48000
TIME=np.arange(-48,59)/RATE
SHIFTS=np.arange(-2,3)/RATE
MAX_EVALUATIONS=70
DIRECTIONS=np.vstack([np.eye(3),-np.eye(3),np.array([[1,1,1],[-1,1,1],[1,-1,1],[1,1,-1]])/np.sqrt(3)])

def prepare(result):
 records=[]
 for j,item in enumerate(result['processed_sessions']):
  session=item['session']
  for o in item['observations']:
   if o['status']!='ok':continue
   i=int(o['capture_id'].split('-')[-1]);response=o['response'];values=np.array(response['values']);axis=response['start_delay_s']+np.arange(len(values))/response['sample_rate_hz'];y=np.interp(TIME,axis,values)
   scale=float(np.interp(0.,axis,values))
   if abs(scale)<.002:continue
   records.append(dict(source=np.array(session['source_position_m']),receiver=np.array(o['receiver_position_m']),source_index=j,receiver_index=i,y=y/scale,observation=o))
 training=[r for r in records if r['receiver_index']<8];held=[r for r in records if r['receiver_index']>=8]
 if any(sum(r['source_index']==j for r in training)<3 for j in range(4)) or len(held)<12:return None
 kernel=np.median(np.array([r['y'] for r in training]),axis=0)
 taper=np.clip((.00075-np.abs(TIME))/.00015,0,1);kernel*=.5-.5*np.cos(np.pi*taper)
 return training,held,kernel

def arrays(records):return np.array([r['source'] for r in records]),np.array([r['receiver'] for r in records]),np.array([r['y'] for r in records])

def delays(parameters,model,s,r,reference,v):
 if model=='single':return np.zeros(len(s)),True
 offset=np.array(parameters[:3]);extra=parameters[3]*1e-4
 if model=='secondary':image=s+offset;valid=True
 else:
  norm=np.linalg.norm(offset)
  if norm<.015:return np.zeros(len(s)),False
  normal=offset/norm;distance=normal@(reference+offset/2);same=(s@normal-distance)*(r@normal-distance)
  if np.any(same<=0):return np.zeros(len(s)),False
  image=s+2*(distance-s@normal)[:,None]*normal;valid=True
 return (np.linalg.norm(image-r,axis=1)-np.linalg.norm(s-r,axis=1))/v+extra,valid

def residual_profiles(parameters,model,records,kernel,reference,v):
 s,r,y=arrays(records);d,valid=delays(parameters,model,s,r,reference,v)
 if not valid:return np.ones_like(y)*5,np.zeros((len(y),2)),np.zeros(len(y))
 best=np.full(len(y),np.inf);residual=np.zeros_like(y);gains=np.zeros((len(y),2));alignment=np.zeros(len(y))
 for shift in SHIFTS:
  a=np.interp(TIME-shift,TIME,kernel,left=0,right=0);aa=a@a;ay=y@a
  if model=='single':
   gain=np.clip(ay/max(aa,1e-15),0,2);res=y-gain[:,None]*a;coeff=np.column_stack([gain,np.zeros(len(y))])
  else:
   b=np.interp((TIME[None,:]-shift-d[:,None]).ravel(),TIME,kernel,left=0,right=0).reshape(y.shape);bb=np.sum(b*b,axis=1);ab=b@a;by=np.sum(b*y,axis=1);det=aa*bb-ab**2;good=det>1e-9
   ga=np.where(good,(ay*bb-by*ab)/np.maximum(det,1e-9),ay/max(aa,1e-15));gb=np.where(good,(by*aa-ay*ab)/np.maximum(det,1e-9),0)
   ga=np.clip(ga,0,2);gb=np.clip(gb,-2,2);res=y-ga[:,None]*a-gb[:,None]*b;coeff=np.column_stack([ga,gb])
  cost=np.mean(res*res,axis=1);use=cost<best;best[use]=cost[use];residual[use]=res[use];gains[use]=coeff[use];alignment[use]=shift
 return residual,gains,alignment

def fit(model,records,kernel,reference,v):
 start=time.perf_counter()
 if model=='single':
  residual,gains,alignment=residual_profiles([],model,records,kernel,reference,v)
  return dict(model=model,parameters=[],training_mse=float(np.mean(residual**2)),runtime_s=time.perf_counter()-start,search_boundary=False,evaluations=1)
 bound=.45 if model=='secondary' else 2.
 starts=[np.r_[d*radius,0.] for radius in ([.12,.3] if model=='secondary' else [.3,1.]) for d in DIRECTIONS]
 best=None;count=0
 for x in starts:
  objective=lambda p:residual_profiles(p,model,records,kernel,reference,v)[0].ravel()
  opt=least_squares(objective,x,bounds=(np.r_[[-bound]*3,-1.5],np.r_[[bound]*3,1.5]),max_nfev=MAX_EVALUATIONS,diff_step=1e-4,ftol=1e-7,xtol=1e-7,gtol=1e-7);count+=opt.nfev;cost=float(np.mean(opt.fun**2))
  if best is None or cost<best[0]:best=(cost,opt)
 cost,opt=best;boundary=bool(np.any(np.abs(opt.x[:3])>bound-.002) or abs(opt.x[3])>1.49)
 return dict(model=model,parameters=opt.x.tolist(),training_mse=cost,runtime_s=time.perf_counter()-start,search_boundary=boundary,evaluations=count,search_starts=len(starts),optimizer_success=bool(opt.success))

def diagnose(result,v=343.):
 prepared=prepare(result)
 if prepared is None:return dict(status='unavailable',reason='Insufficient accepted training/withheld receivers',source_flag=False)
 training,held,kernel=prepared;reference=np.mean([r['source'] for r in training],axis=0);models={}
 for kind in ['single','secondary','plane']:
  fitted=fit(kind,training,kernel,reference,v);res,gains,alignment=residual_profiles(fitted['parameters'],kind,held,kernel,reference,v);fitted.update(held_mse=float(np.mean(res**2)),held_record_mse=np.mean(res**2,axis=1).tolist(),held_component_gains=gains.tolist(),held_alignment_s=alignment.tolist());models[kind]=fitted
 second=models['secondary'];single=models['single'];plane=models['plane'];improvements=np.array(second['held_record_mse'])<np.minimum(single['held_record_mse'],plane['held_record_mse']);strong=sum(abs(g[1])>.1 for g in second['held_component_gains']);flag=bool(second['held_mse']<=.7*min(single['held_mse'],plane['held_mse']) and sum(improvements)>=12 and strong>=12 and not second['search_boundary'])
 return dict(status='source_model_ambiguous' if flag else 'not_qualified',source_flag=flag,models=models,held_improved_count=int(sum(improvements)),strong_secondary_held_count=strong,training_count=len(training),held_count=len(held),kernel=kernel.tolist(),kernel_time_s=TIME.tolist(),reference_m=reference.tolist(),scope='Development waveform compatibility only; no calibrated model probability or geometry correction',pose_timing_budget='Supplied shared calibration is retained by baseline. This prototype profiles +/-2 sample alignment; formal shared-pose sensitivity required before any promotion.')
