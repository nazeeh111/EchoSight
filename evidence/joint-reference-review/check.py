"""Independent saved-trial check. No trial imports, optimizer, raw generation or writes."""
from pathlib import Path
import hashlib,json,itertools,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
P=ROOT/'work/joint-reference-trial'; RAW=ROOT/'work/source-calibration-mismatch/run-v2/raw'
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
freeze=read(P/'freeze.json')
assert sha(P/'freeze.json')=='1b59eb563ba72e29eebf1244a3eb59272e9d8c97f42eaa147d5bac5970e2b941'
for n,h in freeze['source_hashes'].items(): assert sha(P/n)==h,n
for n,h in freeze['input_hashes'].items(): assert sha(ROOT/n)==h,n
assert sha(P/'precheck.json')==freeze['precheck_sha256']
out={'freeze_sha256':sha(P/'freeze.json'),'input_hash_count':len(freeze['input_hashes']),'raw_hash_count':sum(n.endswith('.wav') for n in freeze['input_hashes']),'admissions':[],'fits':[]}
results=read(P/'results.json'); admissions=read(P/'admission.json')
assert results['freeze_sha256']==out['freeze_sha256']
t=np.array(list(range(8))+list(range(12,20))); h=np.array(list(range(8,12))+list(range(20,24)))
checks={}
def close(name,a,b,rtol=1e-9,atol=1e-18):
 a,b=np.asarray(a),np.asarray(b); error=float(np.max(abs(a-b)));checks[name]=error
 assert np.allclose(a,b,rtol=rtol,atol=atol),(name,error)

def prediction(theta,receivers,refs):
 s=theta[:3];v=np.exp(theta[3]); vals=[]
 for n,d in refs:
  q=s+2*(d-n@s)*n
  vals.extend((np.sqrt(np.sum((receivers-q)**2,axis=1))-np.sqrt(np.sum((receivers-s)**2,axis=1)))/v)
 return np.array(vals)

def derive(theta,receivers,refs):
 s=theta[:3];v=np.exp(theta[3]);H=[];D=np.zeros((24,36));G=np.zeros((24,6))
 for j,(n,d) in enumerate(refs):
  axis=np.eye(3)[np.argmin(abs(n))];u=np.cross(n,axis);u/=np.linalg.norm(u);w=np.cross(n,u)
  q=s+2*(d-n@s)*n
  for i,r in enumerate(receivers):
   k=12*j+i; a=q-r;b=s-r;la=np.linalg.norm(a);lb=np.linalg.norm(b);a/=la;b/=lb
   H.append(np.r_[(a-2*n*(n@a)-b)/v,-(la-lb)/v])
   D[k,3*i:3*i+3]=(b-a)/v
   G[k,j*3]=2*(a@n)/v
   for l,e in enumerate((u,w),1):G[k,j*3+l]=2*((d-n@s)*(a@e)-(s@e)*(a@n))/v
 return np.array(H),D,G

def numerical(fn,x,step=1e-6):
 return np.column_stack([(fn(x+np.eye(len(x))[i]*step)-fn(x-np.eye(len(x))[i]*step))/(2*step) for i in range(len(x))])

for pattern in ['single','dual_same_phase','dual_opposite_phase']:
 for seed in [2821,2833]:
  ss=[];rr=[];oo=[];chosen=[];actual=[]
  for plane in ['x','y']:
   folder=RAW/f'{pattern}-{seed}-{plane}';s=read(folder/'session.json');ref=read(folder/'reference.json');o=read(folder/'observations.json');m=read(folder/'manifest.json')
   assert ref['training_capture_ids']==[f'capture-{i:02d}' for i in range(8)]
   assert ref['validation_capture_ids']==[f'capture-{i:02d}' for i in range(8,12)]
   assert ref['source_search_radius_m']==.15 and ref['effective_speed_bounds_m_s']==[300,380]
   assert o.get('source_declaration_consistency',{}).get('status')!='contradictory'
   cs={c['capture_id']:c for c in s['captures']}; os={v['capture_id']:v for v in o['observations']}
   assert set(cs)==set(os)==set(ref['training_capture_ids']+ref['validation_capture_ids'])
   s['captures']=[cs[f'capture-{i:02d}'] for i in range(12)]
   for i,c in enumerate(s['captures']):
    ob=os[c['capture_id']];rp=np.array(c['receiver_position_m']);sp=np.array(s['source_position_m']);n=np.array(ref['normal']);q=sp+2*(ref['offset_m']-n@sp)*n
    ell=np.linalg.norm(q-rp)-np.linalg.norm(sp-rp);window=[max(0,(ell-.3)/380),(ell+.3)/300]
    cc=[v for v in ob['candidates'] if window[0]<=v['delay_s']<=window[1]]
    ok=ob['status']=='ok' and len(cc)==1
    actual.append(dict(reference=plane,capture_id=c['capture_id'],partition='training' if i<8 else 'validation',observation_status=ob['status'],eligible_candidates=len(cc),window_s=window,accepted=ok,candidate_id=cc[0]['candidate_id'] if ok else None))
    assert sha(folder/c['recording_path'])==ob['recording_sha256']==m['raw'][c['recording_path']]
    chosen.append(cc[0] if ok else None);oo.append(ob)
   ss.append(s);rr.append(ref)
  for i in range(12):
   for key in ['receiver_position_m','receiver_position_std_m','receiver_pose_group_id']: assert ss[0]['captures'][i][key]==ss[1]['captures'][i][key]
  for key in ['recording_sha256','waveform_sha256']: assert len(set(ob[key] for ob in oo))==24
  a=next(a for a in admissions if a['seed']==seed and a['pattern']==pattern)
  assert actual==a['records'];assert all(x['accepted'] for x in actual)==a['admitted']
  out['admissions'].append({'pattern':pattern,'seed':seed,'admitted':a['admitted'],'missing':sum(x['eligible_candidates']==0 for x in actual),'ambiguous':sum(x['eligible_candidates']>1 for x in actual)})
  if pattern!='single':continue
  f=read(P/f'fit-{seed}.json');assert f==next(f for f in results['fits'] if f['seed']==seed)
  theta=np.r_[f['source_position_m'],np.log(f['effective_speed_m_s'])];nominal=np.r_[ss[0]['source_position_m'],np.log(ss[0]['sound_speed_m_s']/ss[0]['source_clock_scale'])]
  receivers=np.array([c['receiver_position_m'] for c in ss[0]['captures']]);refs=[(np.array(r['normal']),r['offset_m']) for r in rr]
  tv=np.array([c['delay_std_s']**2+o['direct_std_s']**2+(c['delay_s']*o['clock']['alpha_std']/o['clock']['alpha'])**2 for c,o in zip(chosen,oo)])
  Rvar=np.diag(np.repeat([c['receiver_position_std_m']**2 for c in ss[0]['captures']],3));Qvar=np.diag([x for ref in rr for x in [ref['offset_std_m']**2,ref['normal_std_rad']**2,ref['normal_std_rad']**2]])
  jac_errors={}
  for label,point in [('nominal',nominal),('fit',theta)]:
   H,D,G=derive(point,receivers,refs)
   Hn=numerical(lambda z:prediction(z,receivers,refs),point)
   Dn=numerical(lambda z:prediction(point,receivers+z.reshape(12,3),refs),np.zeros(36))
   def perturb(z):
    adjusted=[]
    for j,(n,d) in enumerate(refs):
     e=np.eye(3)[np.argmin(abs(n))];u=np.cross(n,e);u/=np.linalg.norm(u);w=np.cross(n,u)
     nn=n+z[j*3+1]*u+z[j*3+2]*w;nn/=np.linalg.norm(nn);adjusted.append((nn,d+z[j*3]))
    return prediction(point,receivers,adjusted)
   Gn=numerical(perturb,np.zeros(6))
   jac_errors[label]={'source_log_speed':float(np.max(abs(H-Hn))),'receiver':float(np.max(abs(D-Dn))),'reference':float(np.max(abs(G-Gn)))}
   assert max(jac_errors[label].values())<5e-11
  H,D,G=derive(theta,receivers,refs);H0,D0,G0=derive(nominal,receivers,refs)
  T=np.diag(tv);R=D@Rvar@D.T;Q=G@Qvar@G.T;C=T+R+Q;C0=T+D0@Rvar@D0.T+G0@Qvar@G0.T
  L=np.linalg.cholesky(C0[np.ix_(t,t)]);A=np.linalg.solve(L,H[t]);U,sv,Vt=np.linalg.svd(A,full_matrices=False)
  K=((Vt.T/sv)@U.T)@np.linalg.solve(L,np.eye(16))
  obs=np.array([c['delay_s'] for c in chosen]);pred=prediction(theta,receivers,refs);res=pred-obs;whiten=np.linalg.solve(L,res[t]);inflation=max(1,whiten@whiten/12)
  Cstar=C.copy();Cstar[np.ix_(t,t)]+=(inflation-1)*(T+R)[np.ix_(t,t)]
  Cp=K@Cstar[np.ix_(t,t)]@K.T;cross=C[np.ix_(h,t)]@K.T@H[h].T
  held=C[np.ix_(h,h)]+H[h]@Cp@H[h].T-cross-cross.T
  B=np.zeros((8,24));B[:,h]=np.eye(8);B[:,t]=-H[h]@K
  close(f'{seed}:held_expansion',held,B@Cstar@B.T)
  transform=np.diag([1,1,1,np.exp(theta[3])]);cp=transform@Cp@transform
  for name,v in dict(nominal_covariance=C0,timing=T,receiver=R,reference=Q,fitted_covariance=C,inflated_covariance=Cstar,H=H,K=K,held_residual_covariance=held).items():close(f'{seed}:matrix:{name}',v,f['matrices'][name],atol=1e-16)
  close(f'{seed}:parameter_covariance',cp,f['parameter_covariance'],atol=1e-12)
  close(f'{seed}:prediction',pred,[r['predicted_delay_s'] for r in f['records']])
  close(f'{seed}:observations',obs,[r['observed_delay_s'] for r in f['records']])
  close(f'{seed}:residuals',res,[r['residual_s'] for r in f['records']])
  close(f'{seed}:singular_values',sv,f['information_singular_values'],atol=1e-12)
  close(f'{seed}:optimizer_cost',whiten@whiten/2,f['optimizer']['cost'])
  assert inflation==f['training_noise_inflation']
  # Enumerate every one of the 4096 correlation endpoint assignments; no fitted weights change.
  F=np.zeros((4,24));F[:,t]=transform@K
  signs=np.array(list(itertools.product([-1.,1.],repeat=12)))
  pair_scale=np.sqrt(tv[:12]*tv[12:])*np.r_[np.repeat(inflation,8),np.ones(4)]
  variations_p=signs@(2*F[:,:12]*F[:,12:]*pair_scale).T
  variations_h=signs@(2*B[:,:12]*B[:,12:]*pair_scale).T
  pmax=np.diag(cp)+variations_p.max(axis=0);hmin=np.diag(held)+variations_h.min(axis=0);hmax=np.diag(held)+variations_h.max(axis=0)
  close(f'{seed}:worst_parameter_std',np.sqrt(pmax),f['pair_correlation_worst_parameter_std'],atol=1e-12)
  close(f'{seed}:minimum_held_std',np.sqrt(hmin),f['pair_correlation_min_held_std_s'])
  close(f'{seed}:maximum_held_std',np.sqrt(hmax),f['pair_correlation_max_held_std_s'])
  metric_rows=[]
  for j in range(2):
   train=np.arange(j*12,j*12+8);heldi=np.arange(j*12+8,j*12+12);local=slice(j*4,j*4+4)
   zt=res[train]/np.sqrt(np.diag(T+R)[train]);zh=res[heldi]/np.sqrt(np.diag(held)[local]);zs=res[heldi]/np.sqrt(hmin[local])
   metrics={'training_normalized_rms':np.sqrt(np.mean(zt**2)),'validation_normalized_rms':np.sqrt(np.mean(zh**2)),'validation_max_abs_z':max(abs(zh)),'validation_nominal_rms_s':np.sqrt(np.mean((prediction(nominal,receivers,refs)[heldi]-obs[heldi])**2)),'validation_fitted_rms_s':np.sqrt(np.mean(res[heldi]**2)),'validation_max_abs_residual_s':max(abs(res[heldi]))}
   for name,v in metrics.items():close(f'{seed}:{j}:{name}',v,f['references'][j]['metrics'][name])
   limits={'training_normalized_rms':2.5,'validation_normalized_rms':2.5,'validation_max_abs_z':3.5,'validation_fitted_rms_s':.0001,'validation_max_abs_residual_s':.0002}
   gates={name:bool(metrics[name]<=limit) for name,limit in limits.items()};assert gates==f['references'][j]['gates'] and all(gates.values())
   close(f'{seed}:{j}:sensitivity_rms',np.sqrt(np.mean(zs**2)),f['references'][j]['pair_correlation_sensitivity']['maximum_normalized_rms'])
   close(f'{seed}:{j}:sensitivity_z',max(abs(zs)),f['references'][j]['pair_correlation_sensitivity']['maximum_abs_z'])
   metric_rows.append({k:float(v) for k,v in metrics.items()})
  lo=np.r_[nominal[:3]-.15,np.log(300)];hi=np.r_[nominal[:3]+.15,np.log(380)]
  bg={'optimizer_success':f['optimizer']['success'],'singular_ratio':bool(sv[-1]/sv[0]>=1e-4),'euclidean_radius':bool(np.linalg.norm(theta[:3]-nominal[:3])<.147),'parameter_bound_margin':bool(np.min(theta-lo)>=1e-6 and np.min(hi-theta)>=1e-6)}
  assert bg==f['bound_gates'] and all(bg.values()) and f['passed']
  out['fits'].append({'seed':seed,'jacobian_errors':jac_errors,'metrics':metric_rows,'singular_ratio':float(sv[-1]/sv[0]),'training_noise_inflation':inflation,'receiver_cross_reference_max_s2':float(np.max(abs(R[:12,12:]))),'training_held_cross_max_s2':float(np.max(abs(C[np.ix_(h,t)]))),'held_covariance_min_eigenvalue':float(np.linalg.eigvalsh(held).min()),'held_variance_relative_change_if_cross_terms_omitted':((np.diag(cross+cross.T))/np.diag(held)).tolist(),'parameter_std':np.sqrt(np.diag(cp)).tolist(),'worst_parameter_std':np.sqrt(pmax).tolist(),'gradient_max_abs':float(np.max(abs(A.T@whiten))),'correlation_corners_checked':len(signs)})
assert results['all_single_controls_passed'] and results['branch_decision']=='bounded_development_pass_only'
out['postfit_truth_checks']=[]
for f,e in zip(results['fits'],results['postfit_truth_evaluation']):
 truth=read(RAW/f"single-{f['seed']}-x/truth.json")
 source_error=float(np.linalg.norm(np.array(f['source_position_m'])-truth['primary_m']))
 speed_error=f['effective_speed_m_s']-truth['effective_speed_m_s']
 assert source_error==e['source_error_m'] and speed_error==e['effective_speed_error_m_s']
 out['postfit_truth_checks'].append(dict(seed=f['seed'],source_error_m=source_error,effective_speed_error_m_s=speed_error))
out['max_abs_errors']=checks
(ROOT/'work/review-joint-reference/check.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items() if k!='max_abs_errors'},indent=2))
print('All checks passed. Maximum comparison error:',max(checks.values()))
