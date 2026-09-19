"""Independent archive, frozen-input and local-information checks; no raw generation."""
from pathlib import Path
import hashlib,json,tarfile,subprocess
import numpy as np
ROOT=Path(__file__).resolve().parents[1];P=ROOT/'work/source-calibration-mismatch';ARCHIVE=ROOT/'evidence/source-calibration-mismatch/source-calibration-mismatch-evidence.tar.gz'
sha=lambda x:hashlib.sha256(x).hexdigest()
with tarfile.open(ARCHIVE) as tar:
 members={m.name:tar.extractfile(m).read() for m in tar.getmembers() if m.isfile()}
manifest=json.loads(members['MANIFEST.json'])
assert set(members)==set(manifest['files'])|{'MANIFEST.json'}
assert sha(json.dumps(manifest['files'],sort_keys=True).encode())==manifest['content_sha256']
for name,digest in manifest['files'].items():
 assert sha(members[name])==digest,name
 if name.endswith('/observations.json'):
  local=json.loads((P/name).read_text());archived=json.loads(members[name])
  for o in local['observations']:
   if 'response' in o:o['archived_response_sha256']=sha(json.dumps(o.pop('response')).encode())
  assert local==archived,name
 else:assert (P/name).read_bytes()==members[name],name
frozen=[]
for version in ['v1','v2']:
 freeze=json.loads(members[f'run-{version}/freeze.json'])
 for name,digest in freeze['source_hashes'].items():
  assert sha((P/name).read_bytes())==digest,name
  if name.startswith('core/'):
   assert (P/name).read_bytes()==subprocess.check_output(['git','show',freeze['runtime_commit']+':'+name[len('core/'):]],cwd=ROOT)
 results=json.loads(members[f'run-{version}/results.json']);assert results['source_hashes']==freeze['source_hashes'];assert len(results['rows'])==12
 counts={};raw_count=0;clock_pairs=0
 for row in results['rows']:
  counts[row['result']['status']]=counts.get(row['result']['status'],0)+1
  folder=P/f'run-{version}/raw'/f"{row['pattern']}-{row['seed']}-{row['plane']}"
  m=json.loads((folder/'manifest.json').read_text());assert sha((folder/'truth.json').read_bytes())==m['truth_sha256']
  for path,digest in m['raw'].items():assert sha((folder/path).read_bytes())==digest;raw_count+=1
  cal=json.loads((folder/'calibration.json').read_text());assert cal['status']==row['result']['status']
  ref=json.loads((folder/'reference.json').read_text());assert ref['training_capture_ids']==[f'capture-{i:02d}' for i in range(8)];assert ref['validation_capture_ids']==[f'capture-{i:02d}' for i in range(8,12)]
  if row['plane']=='x':
   counterpart=folder.with_name(folder.name[:-1]+'y')
   sx=json.loads((folder/'session.json').read_text());sy=json.loads((counterpart/'session.json').read_text())
   for x,y in zip(sx['captures'],sy['captures']):assert x['receiver_position_m']==y['receiver_position_m'];assert x['receiver_position_std_m']==y['receiver_position_std_m']
   tx=json.loads((folder/'truth.json').read_text());ty=json.loads((counterpart/'truth.json').read_text())
   assert all(x['alpha']==y['alpha'] and x['offset_s']==y['offset_s'] for x,y in zip(tx['captures'],ty['captures']));clock_pairs+=12
 frozen.append(dict(version=version,outcomes=counts,raw_hashes_checked=raw_count,reused_x_y_clock_draws=clock_pairs))
# Frozen V1 snapshot retains its original failure results byte-for-byte.
for name in ['PROTOCOL.md','run.py','run-v1/freeze.json','run-v1/results.json','run-v1/summary.json']:
 assert (P/'snapshot-b8c1049d8d6d'/name).read_bytes()==members[name]
 assert sha(members[name])==json.loads(members['snapshot-b8c1049d8d6d/MANIFEST.json'])['files'][name]

def read(name):return json.loads(members[name])
def finite(fn,x):
 x=np.array(x,float);cols=[]
 for k in range(len(x)):
  step=2e-6*max(1,abs(x[k]));d=np.zeros(len(x));d[k]=step;cols.append((fn(x+d)-fn(x-d))/(2*step))
 return np.array(cols).T
info=[]
for seed in [2821,2833]:
 sessions=[read(f'run-v2/raw/single-{seed}-{p}/session.json') for p in ['x','y']]
 obs=[read(f'run-v2/raw/single-{seed}-{p}/observations.json')['observations'] for p in ['x','y']]
 refs=[read(f'run-v2/raw/single-{seed}-{p}/reference.json') for p in ['x','y']]
 points=np.array([c['receiver_position_m'] for c in sessions[0]['captures']]);theta=np.r_[sessions[0]['source_position_m'],343.];s=theta[:3];v=theta[3]
 H=[];D=np.zeros((24,36));G=np.zeros((24,6));timing=[];bases=[]
 for j,ref in enumerate(refs):
  n=np.array(ref['normal']);offset=ref['offset_m'];q=s+2*(offset-n@s)*n;M=np.eye(3)-2*np.outer(n,n);axis=np.eye(3)[np.argmin(abs(n))];u=np.cross(n,axis);u/=np.linalg.norm(u);w=np.cross(n,u);bases.append((u,w))
  for i,(r,o) in enumerate(zip(points,obs[j])):
   uq=(q-r)/np.linalg.norm(q-r);us=(s-r)/np.linalg.norm(s-r);f=(np.linalg.norm(q-r)-np.linalg.norm(s-r))/v
   H.append(np.r_[(M@uq-us)/v,-f/v]);D[j*12+i,3*i:3*i+3]=(us-uq)/v
   G[j*12+i,3*j:3*j+3]=[2*(uq@n)/v,*[2*uq@(-(a@s)*n+(offset-n@s)*a)/v for a in (u,w)]]
   candidates=[c for c in o['candidates'] if max(0,(f*v-.3)/380)<=c['delay_s']<=(f*v+.3)/300];assert o['status']=='ok' and len(candidates)==1
   c=candidates[0];timing.append(c['delay_std_s']**2+o['direct_std_s']**2+(c['delay_s']*o['clock']['alpha_std']/o['clock']['alpha'])**2)
 H=np.array(H);timing=np.array(timing)
 def predict(t,rs=points,pert=np.zeros(6)):
  y=[]
  for j,ref in enumerate(refs):
   u,w=bases[j];n=np.array(ref['normal'])+pert[3*j+1]*u+pert[3*j+2]*w;n/=np.linalg.norm(n);q=t[:3]+2*(ref['offset_m']+pert[3*j]-n@t[:3])*n
   y.extend((np.linalg.norm(rs-q,axis=1)-np.linalg.norm(rs-t[:3],axis=1))/t[3])
  return np.array(y)
 errors={'source_speed':float(np.max(abs(H-finite(predict,theta)))),'receiver':float(np.max(abs(D-finite(lambda x:predict(theta,rs=x.reshape(12,3)),points.ravel())))),'reference':float(np.max(abs(G-finite(lambda x:predict(theta,pert=x),np.zeros(6)))))}
 assert max(errors.values())<3e-12,errors
 Rc=np.diag(np.repeat([c['receiver_position_std_m']**2 for c in sessions[0]['captures']],3));Pc=np.diag([x for ref in refs for x in [ref['offset_std_m']**2,ref['normal_std_rad']**2,ref['normal_std_rad']**2]])
 Cpose=D@Rc@D.T;Cplane=G@Pc@G.T;C=np.diag(timing)+Cpose+Cplane
 idx=np.r_[np.arange(8),np.arange(12,20)];covs={};published=[x for x in read('run-v2/joint-information.json')['rows'] if x['seed']==seed][0]
 for label,inds in [('x_only',np.arange(8)),('y_only',np.arange(12,20)),('joint_x_y',idx)]:
  whiten=np.linalg.solve(np.linalg.cholesky(C[np.ix_(inds,inds)]),H[inds]);_,sv,vh=np.linalg.svd(whiten,full_matrices=False);cov=(vh.T/sv**2)@vh;covs[label]=cov
  expected=np.array(published['information'][label]['parameter_covariance']);assert np.allclose(cov,expected,rtol=2e-6,atol=1e-10),(label,np.max(abs(cov-expected)))
 # Independent nuisance-parameter Schur-complement calculation.
 N=np.column_stack([D,G])[idx];prior=np.zeros((42,42));prior[:36,:36]=Rc;prior[36:,36:]=Pc;W=np.diag(1/timing[idx]);A=H[idx]
 block=A.T@W@N;precision=A.T@W@A-block@np.linalg.solve(N.T@W@N+np.linalg.inv(prior),block.T);schur=np.linalg.inv(precision)
 schur_relative=float(np.linalg.norm(schur-covs['joint_x_y'])/np.linalg.norm(schur));assert schur_relative<1e-8
 # Conditional Gaussian linear Monte Carlo, never a raw/joint accuracy claim.
 rng=np.random.default_rng(4521+seed);L=np.linalg.cholesky(C[np.ix_(idx,idx)]);influence=covs['joint_x_y']@A.T@np.linalg.inv(C[np.ix_(idx,idx)]);draws=rng.normal(size=(40000,16))@L.T@influence.T;emp=np.cov(draws,rowvar=False);mc=float(np.linalg.norm(emp-covs['joint_x_y'])/np.linalg.norm(covs['joint_x_y']));assert mc<.04
 decreases={p:float(min(np.linalg.eigvalsh(covs[p]-covs['joint_x_y']))) for p in ['x_only','y_only']};assert min(decreases.values())>-1e-9
 timing_sensitivity={}
 for correlation in [-1.,1.]:
  alternative=C.copy()
  for i in range(12):alternative[i,i+12]+=correlation*np.sqrt(timing[i]*timing[i+12]);alternative[i+12,i]=alternative[i,i+12]
  fit_cov=influence@alternative[np.ix_(idx,idx)]@influence.T
  timing_sensitivity[str(correlation)]=np.sqrt(np.diag(fit_cov)).tolist()
 pair_extra=np.sum(np.abs(2*influence[:,:8]*influence[:,8:]*np.sqrt(timing[:8]*timing[12:20])[None,:]),axis=1)
 worst_pair_std=np.sqrt(np.diag(covs['joint_x_y'])+pair_extra).tolist()
 info.append(dict(seed=seed,individual_worst_unknown_pair_timing_std=worst_pair_std,paired_timing_correlation_sensitivity_std=timing_sensitivity,derivative_max_abs_errors=errors,source_std_m={k:np.sqrt(np.diag(c))[:3].tolist() for k,c in covs.items()},speed_std_m_s={k:float(np.sqrt(c[3,3])) for k,c in covs.items()},covariance_decrease_min_eigenvalues=decreases,schur_relative_error=schur_relative,linear_gaussian_mc_covariance_relative_error=mc,receiver_cross_reference_max_s2=float(np.max(abs(Cpose[:12,12:]))),plane_shared_offdiagonal_max_s2=float(np.max(abs(Cplane-np.diag(np.diag(Cplane)))))))
# Independently recalculate every existing uniquely observable transfer metric.
transfer=[]
for row in read('run-v2/results.json')['transfers']:
 if row['status']=='unique_reference_transfer':
  e=np.array([r['predicted_delay_s']-r['observed_delay_s'] for r in row['records']]);rms=float(np.sqrt(np.mean(e**2)));mx=float(max(abs(e)));assert abs(rms-row['rms_s'])<1e-15;assert abs(mx-row['max_abs_s'])<1e-15
  transfer.append(dict(seed=row['seed'],pattern=row['pattern'],rms_s=rms,max_abs_s=mx,pass_absolute=bool(rms<=.0001 and mx<=.0002)))
 elif row['pattern']=='dual_opposite_phase':assert row['status']=='ambiguous_reference_transfer' and all(r['eligible_candidates']==2 for r in row['records'])
result=dict(archive_sha256=sha(ARCHIVE.read_bytes()),archive_files_verified=len(manifest['files']),archive_local_identical_after_declared_response_hash_transform=True,freeze_and_runtime_git_hashes_verified=True,raw=frozen,information_checks=info,transfer=transfer,reviewed_joint_information_sha256=sha(members['joint_information.py']),scope='Checks conditional local information only; no new raw families and no executed joint fit. Paired renderer reuses clock/noise random draws across reference arrangements; diagonal timing covariance is prospective rather than empirically validated cross-reference timing coverage.')
(ROOT/'work/review-source-calibration.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
