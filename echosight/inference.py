"""Bounded unlabeled first-order reflector inference with explicit null model."""
from itertools import combinations, product
import hashlib
import time
import numpy as np
from scipy.optimize import least_squares, linear_sum_assignment
from scipy.linalg import solve_triangular
from .geometry import image_source, plane_from_image, excess_delay, reflection_point, support_mesh, sphere_intersections

MAX_CANDIDATES = 18
MAX_VIEWS = 32
MAX_PROPOSALS = 24000
MAX_REFINEMENTS = 72
MAX_SURFACES = 10
GATE_M = .075
CLUTTER_COST = 5.0
MISS_COST = 1.0
PLANE_COST = 7.0
SIGMA_REF = 1e-4


class _Cancelled(Exception): pass


def _check(cancel):
    if cancel and cancel(): raise _Cancelled()


def _empty(session,method):
    return dict(schema_version='1.0',session_id=session.get('session_id'),status='no_result',method=method,
                surfaces=[],hypotheses=[],diagnostics=[],guidance=[],dimensions=[],provenance=[],
                assumptions=['stationary effective point source','first-order specular reflectors','surveyed acoustic-center poses'],
                search=dict(max_candidates_per_view=MAX_CANDIDATES,max_proposals=MAX_PROPOSALS,max_refinements=MAX_REFINEMENTS,complete=False),
                uncertainty_semantics='Local covariance conditional on path associations and point-source/plane model; includes declared shared calibration uncertainty, not unmodeled bias.')


def _prepare(session, observations, out):
    try:
        s=np.asarray(session['source_position_m'],float)
        v=float(session.get('sound_speed_m_s',343))/float(session.get('source_clock_scale',1))
        if s.shape!=(3,) or not np.all(np.isfinite(s)) or not 250<v<450: raise ValueError()
    except (KeyError, ValueError, TypeError, ZeroDivisionError):
        out['diagnostics'].append('missing_or_invalid_source_calibration');return None
    rows=[]
    for o in observations[:MAX_VIEWS]:
        if o.get('status')!='ok': continue
        try:
            r=np.asarray(o['receiver_position_m'],float)
            if r.shape!=(3,) or not np.all(np.isfinite(r)) or np.linalg.norm(r-s)<.05: continue
            peaks=[p for p in o.get('candidates',[]) if np.isfinite(p['delay_s']) and 0 < p['delay_s'] < .12 and np.isfinite(p.get('delay_std_s',1e-5)) and p.get('delay_std_s',1e-5)>0 and not p.get('merged',False)]
            peaks=sorted(peaks,key=lambda p: (-abs(p.get('amplitude',1)),p['delay_s']))[:MAX_CANDIDATES]
            if peaks: rows.append(dict(o=o,r=r,peaks=peaks,t=np.array([p['delay_s'] for p in peaks])))
        except (KeyError,ValueError,TypeError):
            out['diagnostics'].append('invalid_observation')
    if len(rows)<4:
        out['diagnostics'].append('insufficient_independent_views_minimum_four');out['guidance'].append(dict(action='Acquire additional surveyed placements with receiver height variation; reuse the same phones.'));return None
    if len(rows)<6: out['diagnostics'].append('few_views_weak_unlabeled_echo_rejection')
    r=np.array([x['r'] for x in rows]);unique=np.unique(np.round(r,4),axis=0)
    if len(unique)<4:
        out['diagnostics'].append('insufficient_distinct_receiver_positions');return None
    if np.linalg.matrix_rank(r-r.mean(axis=0),tol=1e-5)<2:
        out['diagnostics'].append('collinear_receivers_unobservable_rotation');out['status']='ambiguous';return None
    if len(observations)>MAX_VIEWS or any(len(x.get('candidates',[]))>MAX_CANDIDATES for x in observations): out['diagnostics'].append('input_search_subset_limit')
    return s,v,rows,r


def _nearest(q,s,r,v,rows):
    pred=excess_delay(s,r,q,v)
    ids=np.array([np.argmin(abs(x['t']-mu)) for x,mu in zip(rows,pred)])
    err=np.array([x['t'][j]-mu for x,j,mu in zip(rows,ids,pred)])*v
    n,d=plane_from_image(s,q)
    valid=np.array([(n@s-d)*(n@ri-d)>1e-8 for ri in r])
    good=(abs(err)<GATE_M)&valid
    return ids,err,good


def _proposals(s,r,v,rows,method,cancel,out):
    proposals=[]
    if method=='image_source_consensus':
        triples=sorted(combinations(range(len(r)),3),key=lambda ids: -np.linalg.norm(np.cross(r[ids[1]]-r[ids[0]],r[ids[2]]-r[ids[0]])))
        # Two distinct well spread anchor triples tolerate one missing-view path.
        anchors=[triples[0]]
        for tri in triples[1:]:
            if len(set(tri)&set(anchors[0]))<=1:
                anchors.append(tri);break
        for tri in anchors:
            _check(cancel)
            for indices in product(*[range(len(rows[i]['t'])) for i in tri]):
                rho=[np.linalg.norm(r[i]-s)+v*rows[i]['t'][j] for i,j in zip(tri,indices)]
                proposals.extend(sphere_intersections(r[list(tri)],rho))
                if len(proposals)>=MAX_PROPOSALS:
                    out['diagnostics'].append('proposal_budget_reached');return proposals[:MAX_PROPOSALS]
    else:
        count=96;k=np.arange(count);z=(k+.5)/count;phi=k*np.pi*(3-np.sqrt(5));normals=np.column_stack((np.sqrt(1-z*z)*np.cos(phi),np.sqrt(1-z*z)*np.sin(phi),z))
        normals=np.vstack((np.eye(3),normals))
        # All views contribute proposals; same frozen cap as the tuple method.
        for row in rows:
            _check(cancel);ri=row['r'];D=np.linalg.norm(ri-s)
            for t in row['t']:
                E=(D+v*t)**2-D**2
                root=np.sqrt((normals@(s-ri))**2+E);middle=normals@(s+ri)
                for sign in (-1,1):
                    ds=(middle+sign*root)/2
                    proposals.extend(s+2*(ds-normals@s)[:,None]*normals)
                if len(proposals)>=MAX_PROPOSALS:
                    out['diagnostics'].append('proposal_budget_reached');return proposals[:MAX_PROPOSALS]
    return proposals


def _rank_proposals(proposals,s,r,v,rows,cancel):
    ranked=[]
    # Chunked vectorization keeps memory bounded even at the proposal cap.
    for start in range(0,len(proposals),512):
        _check(cancel);qs=np.asarray(proposals[start:start+512]);length=np.linalg.norm(qs-s,axis=1)
        qs=qs[(length>.1)&(length<90)]
        if not len(qs):continue
        pred=(np.linalg.norm(qs[:,None,:]-r[None,:,:],axis=2)-np.linalg.norm(r-s,axis=1))/v
        errs=np.column_stack([np.min(abs(pred[:,i,None]-x['t'][None,:]),axis=1)*v for i,x in enumerate(rows)])
        n=(qs-s)/np.linalg.norm(qs-s,axis=1)[:,None];d=np.sum(n*(qs+s)/2,axis=1)
        valid=(np.sum(n*s,axis=1)-d)[:,None]*(n@r.T-d[:,None])>1e-8
        good=(errs<GATE_M)&valid
        counts=good.sum(axis=1);cost=np.sum(np.minimum(errs/GATE_M,1)**2,axis=1)
        for i in np.where(counts>=4)[0]: ranked.append(((-int(counts[i]),float(cost[i])),qs[i]))
    ranked.sort(key=lambda x:x[0]);selected=[]
    for _,q in ranked:
        if all(np.linalg.norm(q-old)>.15 for old in selected):selected.append(q)
        if len(selected)>=MAX_REFINEMENTS:break
    return selected


def _refine(q,s,r,v,rows):
    for _ in range(3):
        ids,err,good=_nearest(q,s,r,v,rows)
        if good.sum()<4:return None
        target=np.array([x['t'][j] for x,j in zip(rows,ids)])
        fit=least_squares(lambda x:(excess_delay(s,r[good],x,v)-target[good])*v,q,loss='soft_l1',f_scale=.02,max_nfev=35)
        if np.linalg.norm(q-fit.x)<1e-7:q=fit.x;break
        q=fit.x
    ids,err,good=_nearest(q,s,r,v,rows)
    if good.sum()<4:return None
    return q,ids,err,good


def _assign(qs,s,r,v,rows):
    assignments=[];misses=0
    for i,row in enumerate(rows):
        k=len(qs);m=len(row['t']);cost=np.full((k,m+k),1e9)
        for j,q in enumerate(qs):
            n,d=plane_from_image(s,q);mu=float(excess_delay(s,r[i],q,v))
            valid=(n@s-d)*(n@r[i]-d)>1e-8 and 0<mu<.12
            cost[j,m+j]=MISS_COST if valid else 0
            if valid:
                residual=(row['t']-mu)*v
                # Fixed proposal scale avoids rewarding uncertain geometry.
                edge=.5*(residual/.025)**2-CLUTTER_COST
                cost[j,:m]=np.where(abs(residual)<GATE_M,edge,1e9)
        ri,ci=linear_sum_assignment(cost)
        for j,col in zip(ri,ci):
            if col<m:assignments.append((j,i,int(col)))
            elif cost[j,col]>0:misses+=1
    return assignments,misses


def _covariance(qs,assignments,s,r,v,rows,session):
    m=len(assignments);cov=np.zeros((m,m));J=np.zeros((m,3*len(qs)));source_grad=[];scale_grad=[];receiver_grad=[];residual=[]
    source_std=float(session.get('source_position_std_m',.01));c=float(session.get('sound_speed_m_s',343));kappa=float(session.get('source_clock_scale',1))
    vstd=np.hypot(float(session.get('sound_speed_std_m_s',.6))/kappa,v*float(session.get('source_clock_std_ppm',100))*1e-6)
    for a,(k,i,l) in enumerate(assignments):
        q=qs[k];n,d=plane_from_image(s,q);u=(r[i]-s)/np.linalg.norm(r[i]-s);g=(r[i]-q)/np.linalg.norm(r[i]-q);A=np.eye(3)-2*np.outer(n,n)
        mu=float(excess_delay(s,r[i],q,v));p=rows[i]['peaks'][l]
        residual.append(p['delay_s']-mu);cov[a,a]=max(float(p.get('delay_std_s',1e-5)),1e-6)**2
        source_grad.append((u-A@g)/v);receiver_grad.append((g-u)/v);scale_grad.append(-mu/v)
        J[a,3*k:3*k+3]=-g/v
    sg=np.array(source_grad);vg=np.array(scale_grad);cov+=source_std**2*(sg@sg.T)+vstd**2*np.outer(vg,vg)
    for a,(_,i,_) in enumerate(assignments):
        for b,(_,j,_) in enumerate(assignments):
            if i==j:
                cov[a,b]+=float(rows[i]['o'].get('direct_std_s',1e-5))**2
                cov[a,b]+=float(rows[i]['o'].get('receiver_position_std_m',.01))**2*np.dot(receiver_grad[a],receiver_grad[b])
    return np.array(residual),cov,J


def _score(qs,s,r,v,rows,session,required_support=None):
    if not qs:return CLUTTER_COST*sum(len(x['t']) for x in rows),[],None
    assigned,miss=_assign(qs,s,r,v,rows)
    counts=np.bincount([a[0] for a in assigned],minlength=len(qs))
    if np.any(counts<(required_support or min(7,len(rows)))):return np.inf,assigned,None
    e,cov,J=_covariance(qs,assigned,s,r,v,rows,session)
    L=np.linalg.cholesky(cov);whitened=solve_triangular(L,e,lower=True)
    cost=.5*float(whitened@whitened)+float(np.log(np.diag(L)/SIGMA_REF).sum())+.5*len(e)*np.log(2*np.pi)
    cost+=MISS_COST*miss+CLUTTER_COST*(sum(len(x['t']) for x in rows)-len(e))+PLANE_COST*len(qs)
    W=solve_triangular(L,J,lower=True);information=W.T@W
    parameter_cov=np.linalg.pinv(information,rcond=1e-10)
    return cost,assigned,(parameter_cov,e,cov,J)


def _surface(q,k,assignments,covariance,s,r,v,rows,session):
    n,d=plane_from_image(s,q);evidence=[];points=[]
    for ki,i,l in assignments:
        if ki!=k:continue
        point=reflection_point(s,r[i],n,d)
        if point is None:continue
        peak=rows[i]['peaks'][l];pred=float(excess_delay(s,r[i],q,v));points.append(point)
        evidence.append(dict(capture_id=rows[i]['o']['capture_id'],candidate_id=peak['candidate_id'],observed_delay_s=float(peak['delay_s']),predicted_delay_s=pred,residual_s=float(peak['delay_s']-pred),reflection_point_m=point.tolist()))
    vertices,triangles=support_mesh(points,n)
    block=covariance[3*k:3*k+3,3*k:3*k+3];length=np.linalg.norm(q-s)
    # Numerical Jacobian of canonical plane coordinates (local only).
    eps=1e-5;jac=np.zeros((4,3))
    for j in range(3):
        qp=q.copy();qm=q.copy();qp[j]+=eps;qm[j]-=eps;np_,dp=plane_from_image(s,qp);nm,dm=plane_from_image(s,qm)
        if np_@n<0:np_,dp=-np_,-dp
        if nm@n<0:nm,dm=-nm,-dm
        jac[:,j]=(np.r_[np_,dp]-np.r_[nm,dm])/(2*eps)
    pcov=jac@block@jac.T
    sid=hashlib.sha256(('|'.join(sorted(e['capture_id']+':'+e['candidate_id'] for e in evidence))).encode()).hexdigest()[:12]
    return dict(surface_id='reflector-'+sid,kind='unclassified_planar_reflector',normal=n.tolist(),offset_m=d,image_source_m=q.tolist(),support=evidence,vertices_m=vertices,triangles=triangles,extent_status='unknown',mesh_semantics='reflection_support_convex_hull_not_physical_edges',uncertainty=dict(offset_std_m=float(np.sqrt(max(0,pcov[3,3]))),normal_angular_std_rad=float(np.sqrt(max(0,np.trace(pcov[:3,:3])))),image_source_covariance_m2=block.tolist(),conditional_on='associations and first-order point-source model'),confidence=dict(kind='evidence_summary_not_probability',supporting_views=len(evidence),rms_residual_m=float(v*np.sqrt(np.mean([e['residual_s']**2 for e in evidence])))))


def _run(session,observations,cancel,progress,method):
    start=time.perf_counter();out=_empty(session,method)
    try:
        _check(cancel);prepared=_prepare(session,observations,out)
        if prepared is None:return out
        s,v,rows,r=prepared
        if progress:progress(.1,'Generating image-source hypotheses')
        proposals=_proposals(s,r,v,rows,method,cancel,out);out['search']['proposals']=len(proposals)
        selected=_rank_proposals(proposals,s,r,v,rows,cancel);refined=[]
        for q in selected:
            _check(cancel);fit=_refine(q,s,r,v,rows)
            if fit is not None and all(np.linalg.norm(fit[0]-old)>.05 for old in refined):refined.append(fit[0])
        out['search']['refined']=len(selected)
        if len(selected)>=MAX_REFINEMENTS:out['diagnostics'].append('refinement_budget_reached')
        if progress:progress(.55,'Assigning exclusive reflector evidence')
        null,_,_=_score([],s,r,v,rows,session);best=null;qs=[]
        # Greedy complete-model additions preserve exclusive assignments and null.
        for _ in range(MAX_SURFACES):
            _check(cancel);winner=None
            for q in refined:
                if any(np.linalg.norm(q-old)<.05 for old in qs):continue
                score,assign,meta=_score(qs+[q],s,r,v,rows,session)
                if score<best-2.0:
                    winner=(q,score)
                    best=score
            if winner is None:break
            qs.append(winner[0])
        if not qs:
            out['diagnostics'].append('no_model_beats_null');out['score']=dict(null=null,selected=null);return out
        score,assign,meta=_score(qs,s,r,v,rows,session);pcov,e,cov,J=meta
        out['surfaces']=[_surface(q,k,assign,pcov,s,r,v,rows,session) for k,q in enumerate(qs)]
        out['score']=dict(null=null,selected=score,kind='dimensionless_full_covariance_ranking_not_posterior',clutter_cost=CLUTTER_COST,miss_cost=MISS_COST,plane_cost=PLANE_COST)
        out['shared_image_source_covariance_m2']=pcov.tolist()
        out['status']='ok' if len(rows)>=7 else 'partial'
        # Fewer than seven independent surveyed views leave correspondence risk
        # unresolved. Preserve the fit as candidates, not definitive surfaces.
        if len(rows)<7:
            out['hypotheses'].append(dict(hypothesis_id='unconfirmed_correspondences',surfaces=out['surfaces'],reason='Fewer than seven independent receiver views; acquire confirmation placements.'))
            out['surfaces']=[]
            out['status']='ambiguous'
        candidates=[]
        for q in refined:
            if any(np.linalg.norm(q-old)<.15 for old in qs):continue
            cs,ca,cm=_score([q],s,r,v,rows,session,required_support=4)
            if cm is not None and cs<null-2:
                candidate=_surface(q,0,ca,cm[0],s,r,v,rows,session)
                candidates.append(candidate)
            if len(candidates)>=8:break
        if candidates:
            out['hypotheses'].append(dict(hypothesis_id='unconfirmed_candidates',surfaces=candidates,reason='Alternative individual fits; not independent resolved structure. Candidate evidence may overlap other hypotheses.'))
        # Global coplanar symmetry includes source as well as receivers.
        allpos=np.vstack((s,r));center=allpos.mean(axis=0);_,singular,Vh=np.linalg.svd(allpos-center,full_matrices=False)
        if singular[-1]<1e-5:
            normal=Vh[-1];mirrors=[q-2*np.dot(q-center,normal)*normal for q in qs]
            if any(np.linalg.norm(q-qm)>.05 for q,qm in zip(qs,mirrors)):
                out['status']='ambiguous';out['diagnostics'].append('global_coplanar_mirror_ambiguity')
                out['hypotheses']=[dict(hypothesis_id='primary',surface_ids=[x['surface_id'] for x in out['surfaces']],image_sources_m=[q.tolist() for q in qs]),dict(hypothesis_id='coplanar_mirror',image_sources_m=[q.tolist() for q in mirrors],planes=[dict(normal=plane_from_image(s,q)[0].tolist(),offset_m=plane_from_image(s,q)[1]) for q in mirrors])]
                out['hypotheses'][0]['surfaces']=out['surfaces'];out['surfaces']=[]
                out['guidance'].append(dict(action='Change receiver height and survey its new position to distinguish mirror alternatives.',suggested_position_m=(r[0]+.8*normal).tolist(),reason='Same-plane additional captures cannot remove this global ambiguity.'))
        for a,b in combinations(range(len(out['surfaces'])),2):
            pa,pb=out['surfaces'][a],out['surfaces'][b];na=np.array(pa['normal']);nb=np.array(pb['normal']);dot=float(na@nb)
            if abs(dot)>np.cos(np.deg2rad(3)) and out['status']!='ambiguous':
                sign=1 if dot>0 else -1;sep=abs(pa['offset_m']-sign*pb['offset_m'])
                grad=np.zeros(3*len(qs));eps=1e-5
                for idx,factor in ((a,1.),(b,-sign)):
                    for axis in range(3):
                        plus=qs[idx].copy();minus=qs[idx].copy();plus[axis]+=eps;minus[axis]-=eps
                        grad[3*idx+axis]=factor*(plane_from_image(s,plus)[1]-plane_from_image(s,minus)[1])/(2*eps)
                sepstd=float(np.sqrt(max(0,grad@pcov@grad)))
                out['dimensions'].append(dict(kind='near_parallel_plane_separation',surface_ids=[pa['surface_id'],pb['surface_id']],value_m=sep,std_m=sepstd,normal_angle_rad=float(np.arccos(np.clip(abs(dot),0,1))),semantics='Plane separation; not a proven enclosed room dimension.',uncertainty_note='See shared joint covariance; local normals are not exactly parallel.'))
        if not out['guidance']:out['guidance'].append(dict(action='Add surveyed views around weakly supported reflectors with a different height.',suggested_position_m=(r.mean(axis=0)+np.array([.35,-.25,.6])).tolist(),reason='Finite support and missing echoes do not establish physical edges or empty space.'))
        out['provenance']=sorted(set(o.get('provenance','unspecified') for o in observations))
        out['search']['complete']=not any('budget' in str(x) or 'limit' in str(x) for x in out['diagnostics'])
        out['search']['global_optimality_proven']=False
        if not out['search']['complete'] and out['status']=='ok':out['status']='partial'
        if progress:progress(1.,'Inference complete')
        return out
    except _Cancelled:
        out['status']='cancelled';out['diagnostics'].append('cancelled_by_caller');return out
    finally:
        out['runtime_s']=time.perf_counter()-start


def infer_scene(session, observations, cancel=None, progress=None):
    return _run(session,observations,cancel,progress,'image_source_consensus')


def infer_baseline(session, observations):
    """Independent direct-plane grid initializer, identical observations/scoring."""
    return _run(session,observations,None,None,'direct_plane_grid_baseline')


def infer_first_echo(session, observations):
    """Simple earliest-echo baseline with the correct bistatic forward model.

    One candidate per receiver assumes the first returned echo belongs to the
    same reflector across views. That assumption frequently fails in rooms.
    """
    filtered=[dict(o,candidates=sorted(o.get('candidates',[]),key=lambda p:p['delay_s'])[:1]) for o in observations]
    out=_run(session,filtered,None,None,'image_source_consensus')
    out['method']='earliest_echo_bistatic_baseline'
    out['assumptions'].append('earliest detected echo correspondence across receivers')
    return out
