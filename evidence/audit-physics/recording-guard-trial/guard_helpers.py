# Isolated experiment, fixed analytic-stage parameters; no main runtime changes.
from itertools import permutations as _permutations
_PERMS=np.array(list(_permutations(range(6))),int)

def _held_select(session,observations,s,v,rows,r,out,cancel):
    _check(cancel)
    if len(rows)<12:
        out['held_guard']=dict(status='unavailable',reason='requires_twelve_valid_independent_views',valid_view_count=len(rows),calibrated=False)
        return None
    # Acquisition order fixed in advance; only the first12 valid independent rows.
    chosen=rows[:12];train=chosen[::2];held=chosen[1::2];rt=np.array([row['r'] for row in train]);rh=np.array([row['r'] for row in held])
    out['held_guard']=dict(status='evaluated',valid_view_count=len(rows),training_capture_ids=[x['o']['capture_id'] for x in train],validation_capture_ids=[x['o']['capture_id'] for x in held],permutations=720,threshold=.01,scope='Conditional exchangeable global null; not a physical first-order probability',no_validation_refit_before_test=True,calibrated=False)
    proposals=_proposals(s,rt,v,train,'image_source_consensus',cancel,out);out['search']['proposals']=len(proposals)
    selected=_rank_proposals(proposals,s,rt,v,train,cancel);qs=[]
    for q in selected:
        _check(cancel);fit=_refine(q,s,rt,v,train)
        if fit is not None and all(np.linalg.norm(fit[0]-old)>.05 for old in qs):qs.append(fit[0])
    out['search']['refined']=len(selected)
    if len(selected)>=MAX_REFINEMENTS:out['diagnostics'].append('refinement_budget_reached')
    if not qs:
        out['held_guard']['training_hypotheses']=0;out['held_guard']['accepted_prerefit']=[];return []
    qs=np.asarray(qs);prediction=(np.linalg.norm(qs[:,None,:]-rh[None,:,:],axis=2)-np.linalg.norm(rh-s,axis=1))/v
    costs=[]
    for row in held:
        _check(cancel);costs.append(np.min(np.abs(prediction[:,:,None]-row['t'][None,None,:]),axis=2))
    weights=np.exp(-.5*(np.asarray(costs).transpose(1,2,0)*v/.025)**2)
    n=(qs-s)/np.linalg.norm(qs-s,axis=1)[:,None];d=np.einsum('ij,ij->i',n,(qs+s)/2)
    valid=(n@s-d)[:,None]*(n@rh.T-d[:,None])>1e-8;eligible=valid.sum(axis=1)>=4;weights*=valid[:,:,None]
    maximum=[]
    for start in range(0,720,60):
        _check(cancel);statistics=weights[:,np.arange(6)[None,:],_PERMS[start:start+60]].sum(axis=2);statistics[~eligible,:]=-np.inf;maximum.extend(statistics.max(axis=0))
    maximum=np.array(maximum);identity=np.arange(6);observed=weights[:,identity,identity].sum(axis=1);pvalue=np.mean(maximum[None,:]>=observed[:,None]-1e-12,axis=1)
    accepted=[];evidence=[]
    for index in np.flatnonzero(eligible&(pvalue<=.01)):
        q=qs[index]
        if any(np.linalg.norm(q-old)<.15 for old in accepted):continue
        accepted.append(q);evidence.append(dict(image_source_m=q.tolist(),validation_pvalue=float(pvalue[index]),validation_statistic=float(observed[index]),semantics='Training image before all-record refit; conditional global-null evidence only'))
    out['held_guard'].update(training_hypotheses=len(qs),accepted_prerefit=evidence,maximum_statistics=[None if not np.isfinite(x) else float(x) for x in maximum])
    return accepted

def _joint_refit(qs,s,r,v,rows,session,out,cancel):
    before=out['held_guard']['accepted_prerefit']
    out['held_guard']['selected_prerefit']=[next(item for item in before if np.linalg.norm(q-np.array(item['image_source_m']))<1e-7) for q in qs]
    diagnostics=[]
    for iteration in range(3):
        _check(cancel);before,assign,meta=_score(qs,s,r,v,rows,session)
        if meta is None:break
        L=np.linalg.cholesky(meta[2])
        def residual(flat):
            _check(cancel);Q=flat.reshape(-1,3);e=np.array([rows[i]['t'][l]-excess_delay(s,r[i],Q[k],v) for k,i,l in assign]);return solve_triangular(L,e,lower=True)
        fit=least_squares(residual,np.asarray(qs).ravel(),max_nfev=35);proposed=list(fit.x.reshape(-1,3));after,_,_= _score(proposed,s,r,v,rows,session)
        diagnostics.append(dict(iteration=iteration,score_before=float(before),score_after=float(after) if np.isfinite(after) else None,nfev=fit.nfev,accepted=bool(after<before)))
        if not after<before:break
        displacement=np.linalg.norm(np.asarray(qs)-np.asarray(proposed));qs=proposed
        if displacement<1e-7:break
    out['held_guard']['joint_refit']=diagnostics
    return qs

def _attach_validation(out,qs,covariance):
    before=out['held_guard']['selected_prerefit']
    for surf,evidence in zip(out['surfaces'],before):surf['validation_before_refit']=evidence
    evidence=[(x['capture_id'],x['candidate_id']) for surf in out['surfaces'] for x in surf['support']]
    if len(set(evidence))!=len(evidence):raise ValueError('Exclusive assignment violated')
    cov=np.asarray(covariance)
    if not np.all(np.isfinite(cov)) or np.linalg.eigvalsh((cov+cov.T)/2).min() < -1e-10*max(np.max(np.abs(cov)),1e-30):raise ValueError('Invalid joint covariance')
