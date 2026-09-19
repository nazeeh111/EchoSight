"""Post-evaluation diagnosis only; no tuning or truth enters training search."""
import json
import numpy as np
from run import ROOT,guard_inference as g
from echosight.geometry import image_source,plane_from_image
from evaluation.metrics import score_surfaces
reports=[]
for name in ['room-211','room-223','room-227','reflector-233']:
 before=json.loads((ROOT/'results'/f'twelve-{name}-matched_filter-original.json').read_text());after=json.loads((ROOT/'results'/f'twelve-{name}-matched_filter-held_guard.json').read_text());session=before['acquisition'];observations=before['observations'];out=g._empty(session,'diagnose');s,v,rows,r=g._prepare(session,observations,out);stored=[];original=g._refine
 def refined(*args,**kwargs):
  fit=original(*args,**kwargs)
  if fit is not None:stored.append(fit[0].copy())
  return fit
 g._refine=refined
 try:g._held_select(session,observations,s,v,rows,r,out,None)
 finally:g._refine=original
 qs=[]
 for q in stored:
  if all(np.linalg.norm(q-old)>.05 for old in qs):qs.append(q)
 Q=np.array(qs);held=rows[:12][1::2];train=rows[:12][::2];rh=np.array([row['r'] for row in held]);pred=(np.linalg.norm(Q[:,None,:]-rh[None,:,:],axis=2)-np.linalg.norm(rh-s,axis=1))/v
 cost=np.array([np.min(abs(pred[:,:,None]-row['t'][None,None,:]),axis=2) for row in held]);weights=np.exp(-.5*(cost.transpose(1,2,0)*v/.025)**2)
 n=(Q-s)/np.linalg.norm(Q-s,axis=1)[:,None];d=np.einsum('ij,ij->i',n,(Q+s)/2);valid=(n@s-d)[:,None]*(n@rh.T-d[:,None])>1e-8;weights*=valid[:,:,None];obs=weights[:,np.arange(6),np.arange(6)].sum(axis=1);maximum=np.array(out['held_guard']['maximum_statistics'],float);p=np.mean(maximum[None,:]>=obs[:,None]-1e-12,axis=1)
 # Now and only now open truth for diagnosis.
 from run import REPO
 truth=json.loads((REPO/'work/physics-estimator/control-twelve'/name/'truth.json').read_text());b=score_surfaces(before,truth);a=score_surfaces(after,truth);missing={m['truth_id'] for m in b['matches']}-{m['truth_id'] for m in a['matches']};details=[]
 for t in truth['surfaces']:
  tid=t.get('surface_id')
  if tid not in missing:continue
  candidates=[]
  for i,q in enumerate(qs):
   normal,offset=plane_from_image(s,q);m=score_surfaces(dict(surfaces=[dict(normal=normal.tolist(),offset_m=offset)]),dict(surfaces=[t]));candidates.append(i) if m['matched_count'] else None
  def support(trueq,subset):
   values=[]
   for row in subset:
    prediction=float(g.excess_delay(s,row['r'],trueq,v));values.append(float(np.min(abs(row['t']-prediction))*v))
   return values
  trueq=image_source(s,t['normal'],t['offset_m']);details.append(dict(truth_id=tid,admissible_training_hypotheses=len(candidates),best_compatible_pvalue=min([float(p[i]) for i in candidates],default=None),best_compatible_statistic=max([float(obs[i]) for i in candidates],default=None),true_plane_nearest_train_residual_m=support(trueq,train),true_plane_nearest_held_residual_m=support(trueq,held)))
 reports.append(dict(case=name,lost_surfaces=details))
(ROOT/'lost-surface-diagnosis.json').write_text(json.dumps(reports,indent=2)+'\n');print(json.dumps(reports,indent=2))
