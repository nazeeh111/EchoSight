"""Experimental equal-input source versus near-reflector waveform comparison."""
from pathlib import Path
import time
import numpy as np
from scipy.optimize import least_squares
from gain_v4 import bounded_gains

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
 if model=='single':return np.zeros(len(s)),np.zeros(len(s),dtype=bool)
 offset=np.array(parameters[:3]);extra=parameters[3]*1e-4
 if model=='secondary':image=s+offset;valid=np.ones(len(s),dtype=bool)
 else:
  norm=np.linalg.norm(offset)
  if norm<.015:return np.zeros(len(s)),np.zeros(len(s),dtype=bool)
  normal=offset/norm;distance=normal@(reference+offset/2);valid=(s@normal-distance)*(r@normal-distance)>0
  image=s+2*(distance-s@normal)[:,None]*normal
 return (np.linalg.norm(image-r,axis=1)-np.linalg.norm(s-r,axis=1))/v+extra,valid

def residual_profiles(parameters,model,records,kernel,reference,v):
 s,r,y=arrays(records);d,valid=delays(parameters,model,s,r,reference,v)
 best=np.full(len(y),np.inf);residual=np.zeros_like(y);gains=np.zeros((len(y),2));alignment=np.zeros(len(y))
 for shift in SHIFTS:
  a=np.interp(TIME-shift,TIME,kernel,left=0,right=0);aa=a@a;ay=y@a
  if model=='single':
   gain=np.clip(ay/max(aa,1e-15),0,2);res=y-gain[:,None]*a;coeff=np.column_stack([gain,np.zeros(len(y))])
  else:
   b=np.interp((TIME[None,:]-shift-d[:,None]).ravel(),TIME,kernel,left=0,right=0).reshape(y.shape);b[~valid]=0.
   coeff,res=bounded_gains(a,b,y)
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

 support_counts=[sum(abs(g[1])>.1 for g,r in zip(second['held_component_gains'],held) if r['source_index']==j) for j in range(4)]
 source_positions=np.array([item['session']['source_position_m'] for item in result['processed_sessions']]);selected=[j for j,count in enumerate(support_counts) if count>=3]
 supported=source_positions[selected];singular=np.linalg.svd(supported-supported.mean(axis=0),compute_uv=False) if len(supported) else np.array([])
 tolerance=max(.03,6*max(item['session'].get('source_position_std_m',0.) for item in result['processed_sessions']))
 identifiable=bool(len(selected)==4 and len(singular)==3 and singular[-1]>tolerance)
 waveform_flag=flag;flag=flag and identifiable
 return dict(status='source_model_ambiguous' if flag else 'not_qualified',source_flag=flag,waveform_flag_before_identifiability=waveform_flag,component_held_support_counts=support_counts,component_source_singular_values_m=singular.tolist(),component_minimum_span_m=tolerance,component_identifiable=identifiable,constant_source_orientation_assumed=True,models=models,held_improved_count=int(sum(improvements)),strong_secondary_held_count=strong,training_count=len(training),held_count=len(held),kernel=kernel.tolist(),kernel_time_s=TIME.tolist(),reference_m=reference.tolist(),scope='Development waveform compatibility only; no calibrated model probability or geometry correction',pose_timing_budget='Supplied shared calibration is retained by baseline. This prototype profiles +/-2 sample alignment; formal shared-pose sensitivity required before any promotion.')
