"""Bounded unlabeled first-order reflector inference with explicit null model."""
from itertools import combinations, product
import hashlib
import time
import numpy as np
from scipy.optimize import least_squares, linear_sum_assignment
from scipy.linalg import solve_triangular
from .geometry import image_source, plane_from_image, excess_delay, reflection_point, support_mesh, sphere_intersections, reflection_path

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



def _effective_speed(session):
    """Metres per nominal source-buffer second, not necessarily physical c."""
    if 'effective_speed_m_s' in session:
        return float(session['effective_speed_m_s'])
    return float(session.get('sound_speed_m_s',343))/float(session.get('source_clock_scale',1))


def _calibration_covariance(session,v):
    """Joint [source x,y,z,effective speed] covariance without double counting."""
    if 'effective_speed_m_s' in session or 'source_effective_speed_covariance' in session:
        if 'effective_speed_m_s' not in session or 'source_effective_speed_covariance' not in session:
            raise ValueError('Effective speed and joint calibration covariance must be supplied together')
        covariance=np.asarray(session['source_effective_speed_covariance'],float)
        if covariance.shape!=(4,4) or not np.all(np.isfinite(covariance)):
            raise ValueError('Joint calibration covariance must be finite 4 by 4')
        if not np.allclose(covariance,covariance.T,rtol=1e-8,atol=1e-12):
            raise ValueError('Joint calibration covariance must be symmetric')
        covariance=(covariance+covariance.T)/2
        if np.linalg.eigvalsh(covariance).min() < -1e-12:
            raise ValueError('Joint calibration covariance must be positive semidefinite')
        return covariance
    source_std=float(session.get('source_position_std_m',.01))
    kappa=float(session.get('source_clock_scale',1))
    vstd=np.hypot(float(session.get('sound_speed_std_m_s',.6))/kappa,v*float(session.get('source_clock_std_ppm',100))*1e-6)
    return np.diag([source_std**2]*3+[vstd**2])

def _empty(session,method):
    return dict(schema_version='1.0',session_id=session.get('session_id'),status='no_result',method=method,
                surfaces=[],hypotheses=[],diagnostics=[],guidance=[],dimensions=[],provenance=[],
                assumptions=['stationary effective point source','first-order specular reflectors','surveyed acoustic-center poses'],
                search=dict(max_candidates_per_view=MAX_CANDIDATES,max_proposals=MAX_PROPOSALS,max_refinements=MAX_REFINEMENTS,complete=False),
                uncertainty_semantics='Local covariance conditional on path associations and point-source/plane model; includes declared shared calibration uncertainty, not unmodeled bias.')


def _prepare(session, observations, out):
    try:
        s=np.asarray(session['source_position_m'],float)
        v=_effective_speed(session)
        if s.shape!=(3,) or not np.all(np.isfinite(s)) or not 250<=v<=460: raise ValueError()
        _calibration_covariance(session,v)
        for key,default in (('source_position_std_m',.01),('sound_speed_std_m_s',.6),('source_clock_std_ppm',100)):
            std=float(session.get(key,default))
            if not np.isfinite(std) or std<0:raise ValueError()
    except (KeyError, ValueError, TypeError, ZeroDivisionError):
        out['diagnostics'].append('missing_or_invalid_source_calibration');return None
    rows=[]
    for o in observations[:MAX_VIEWS]:
        if o.get('status')!='ok': continue
        try:
            r=np.asarray(o['receiver_position_m'],float)
            if r.shape!=(3,) or not np.all(np.isfinite(r)) or np.linalg.norm(r-s)<.05: continue
            for key,default in (('receiver_position_std_m',.01),('direct_std_s',1e-5)):
                std=float(o.get(key,default))
                if not np.isfinite(std) or std<0:raise ValueError()
            clock=o.get('clock',{});alpha=float(clock.get('alpha',1));astd=float(clock.get('alpha_std',0))
            if not np.isfinite(alpha) or alpha<=0 or not np.isfinite(astd) or astd<0:raise ValueError()
            if any(old['o']['capture_id']==o['capture_id'] for old in rows):raise ValueError()
            peaks=[p for p in o.get('candidates',[]) if np.isfinite(p['delay_s']) and 0 < p['delay_s'] < .12 and np.isfinite(p.get('delay_std_s',1e-5)) and p.get('delay_std_s',1e-5)>0 and not p.get('merged',False)]
            peaks=sorted(peaks,key=lambda p: (-abs(p.get('amplitude',1)),p['delay_s']))[:MAX_CANDIDATES]
            if peaks:
                if any(np.linalg.norm(r-old['r'])<.01 for old in rows):
                    out['diagnostics'].append('repeated_receiver_position_not_independent_view');continue
                rows.append(dict(o=o,r=r,peaks=peaks,t=np.array([p['delay_s'] for p in peaks])))
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
        # Add local triples: a finite/interior reflector can be visible only
        # from one side, which maximum-aperture triples may always straddle.
        for i in range(len(r)):
            near=np.argsort(np.linalg.norm(r-r[i],axis=1))[1:4]
            for pair in combinations(near,2):
                tri=tuple(sorted((i,int(pair[0]),int(pair[1]))))
                if tri not in anchors and np.linalg.norm(np.cross(r[tri[1]]-r[tri[0]],r[tri[2]]-r[tri[0]]))>.1:
                    anchors.append(tri);break
            if len(anchors)>=10:break
        out['search']['anchor_triples']=[list(x) for x in anchors]
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
        counts=good.sum(axis=1)
        # Inadmissible opposite-side links are not visibility opportunities.
        # Residual quality competes with count so coherent finite reflectors
        # do not disappear behind numerous loose accidental associations.
        cost=-counts+.25*np.sum(np.where(good,(errs/.025)**2,0),axis=1)+.2*np.sum(valid&~good,axis=1)
        for i in np.where(counts>=4)[0]: ranked.append(((float(cost[i]),-int(counts[i])),qs[i]))
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
    calibration_covariance=_calibration_covariance(session,v)
    for a,(k,i,l) in enumerate(assignments):
        q=qs[k];n,d=plane_from_image(s,q);u=(r[i]-s)/np.linalg.norm(r[i]-s);g=(r[i]-q)/np.linalg.norm(r[i]-q);A=np.eye(3)-2*np.outer(n,n)
        mu=float(excess_delay(s,r[i],q,v));p=rows[i]['peaks'][l]
        residual.append(p['delay_s']-mu);cov[a,a]=max(float(p.get('delay_std_s',1e-5)),1e-6)**2
        source_grad.append((u-A@g)/v);receiver_grad.append((g-u)/v);scale_grad.append(-mu/v)
        J[a,3*k:3*k+3]=-g/v
    calibration_jacobian=np.column_stack((np.array(source_grad),np.array(scale_grad)))
    cov+=calibration_jacobian@calibration_covariance@calibration_jacobian.T
    for a,(_,i,_) in enumerate(assignments):
        for b,(_,j,_) in enumerate(assignments):
            if i==j:
                cov[a,b]+=float(rows[i]['o'].get('direct_std_s',1e-5))**2
                clock=rows[i]['o'].get('clock',{});relative_slope_std=float(clock.get('alpha_std',0))/float(clock.get('alpha',1))
                cov[a,b]+=rows[i]['t'][assignments[a][2]]*rows[j]['t'][assignments[b][2]]*relative_slope_std**2
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
    local_jac=np.array([(q-r[i])/np.linalg.norm(q-r[i]) for ki,i,l in assignments if ki==k])
    local_rank=int(np.linalg.matrix_rank(local_jac,tol=1e-6))
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
    return dict(surface_id='reflector-'+sid,kind='unclassified_planar_reflector',model_status='conditional_first_order_hypothesis',normal=n.tolist(),offset_m=d,image_source_m=q.tolist(),support=evidence,vertices_m=vertices,triangles=triangles,extent_status='unknown',mesh_semantics='reflection_support_convex_hull_not_physical_edges',uncertainty=dict(local_information_rank=local_rank,rank_deficient=local_rank<3,offset_std_m=float(np.sqrt(max(0,pcov[3,3]))),normal_angular_std_rad=float(np.sqrt(max(0,np.trace(pcov[:3,:3])))) if local_rank==3 else None,image_source_covariance_m2=block.tolist() if local_rank==3 else None,conditional_on='associations and first-order point-source model',excluded_model_errors=['reflection_order','multiple_emitters','unmodeled_transducer_response']),confidence=dict(kind='evidence_summary_not_probability',supporting_views=len(evidence),rms_residual_m=float(v*np.sqrt(np.mean([e['residual_s']**2 for e in evidence])))))



def _local_plane_intersections(source, qa, qb):
    """Intersect two planes with their mean-normal line through source.

    Relative coordinates avoid origin-dependent offset subtraction. Each image
    source defines its plane relative to the supplied source acoustic center.
    """
    ra=np.asarray(qa)-source;rb=np.asarray(qb)-source
    la=np.linalg.norm(ra);lb=np.linalg.norm(rb);na=ra/la;nb=rb/lb
    sign=1. if na@nb>=0 else -1.
    direction=na+sign*nb;direction/=np.linalg.norm(direction)
    ta=la/(2*float(na@direction));tb=lb/(2*float(nb@direction))
    points=np.array([source+ta*direction,source+tb*direction])
    # Sensitivity to moving the reference line while holding both physical
    # planes and their mean-normal direction fixed (sign immaterial to norm).
    reference_gradient=na/float(na@direction)-nb/float(nb@direction)
    return abs(tb-ta),direction,points,reference_gradient


def _compose_image(source,qa,qb):
    na,da=plane_from_image(source,qa);nb,db=plane_from_image(source,qb)
    return image_source(image_source(source,na,da),nb,db)


def _second_order_explanations(qs,assignments,parameter_cov,s,r,v,rows,session,cancel):
    """Find alternate two-bounce explanations; do not prove a plane absent."""
    explanations=[];source_covariance=_calibration_covariance(session,v)[:3,:3]
    source_std=float(np.sqrt(max(0,np.linalg.eigvalsh(source_covariance).max())))
    for target in range(len(qs)):
        _check(cancel)
        supported=[(i,l) for k,i,l in assignments if k==target]
        for a,b in combinations([k for k in range(len(qs)) if k!=target],2):
            orders=[]
            for first,second in ((a,b),(b,a)):
                composite=_compose_image(s,qs[first],qs[second]);delta=qs[target]-composite
                # A broad prefilter avoids numerical derivatives for distant
                # models. The actual gate below uses shared joint uncertainty.
                blocks=[parameter_cov[3*k:3*k+3,3*k:3*k+3] for k in (target,first,second)]
                radius=.03+6*np.sqrt(sum(max(0,float(np.trace(x))) for x in blocks))+8*source_std
                if np.linalg.norm(delta)>radius:continue
                jac=np.zeros((3,3*len(qs)));jac[:,3*target:3*target+3]=np.eye(3);eps=1e-5
                for local,k in enumerate((first,second)):
                    for axis in range(3):
                        plus=[qs[first].copy(),qs[second].copy()];minus=[qs[first].copy(),qs[second].copy()]
                        plus[local][axis]+=eps;minus[local][axis]-=eps
                        jac[:,3*k+axis]-=(_compose_image(s,*plus)-_compose_image(s,*minus))/(2*eps)
                sj=np.zeros((3,3))
                for axis in range(3):
                    sp=s.copy();sm=s.copy();sp[axis]+=eps;sm[axis]-=eps
                    sj[:,axis]=-(_compose_image(sp,qs[first],qs[second])-_compose_image(sm,qs[first],qs[second]))/(2*eps)
                # Source/reference and inferred geometry are correlated, but
                # separate cross terms are not stored. 2(A+B) bounds their sum
                # covariance for arbitrary cross correlation; no posterior claim.
                covariance=2*(jac@parameter_cov@jac.T+sj@source_covariance@sj.T)+np.eye(3)*1e-12
                distance=float(delta@np.linalg.solve(covariance,delta))
                if distance<=16.27:
                    orders.append((first,second,composite,distance))
            if not orders:continue
            evidence=[]
            for i,l in supported:
                choices=[]
                for first,second,composite,distance in orders:
                    planes=[plane_from_image(s,qs[k]) for k in (first,second)]
                    path=reflection_path(s,r[i],planes)
                    if path is None:continue
                    mu=(path['length_m']-np.linalg.norm(r[i]-s))/v
                    residual=rows[i]['t'][l]-mu
                    if abs(residual)*v<=GATE_M:
                        choices.append((abs(residual),dict(capture_id=rows[i]['o']['capture_id'],candidate_id=rows[i]['peaks'][l]['candidate_id'],reflection_order_indices=[first,second],predicted_delay_s=float(mu),residual_s=float(residual),path=path)))
                if choices:evidence.append(min(choices,key=lambda item:item[0])[1])
            if len(evidence)>=7 and len(evidence)>=.8*len(supported):
                explanations.append(dict(target_index=target,parent_indices=[a,b],support=evidence,
                    image_source_difference_m=min(float(np.linalg.norm(qs[target]-x[2])) for x in orders),
                    standardized_image_difference=min(x[3] for x in orders),
                    uncertainty_semantics='Conservative shared-covariance compatibility gate, not model probability.',
                    conclusion='First-order reflector and higher-order path interpretations remain competing explanations.'))
                break
    return explanations


def _source_discrimination_guidance(explanation,qs,s,r,v):
    target=explanation['target_index'];a,b=explanation['parent_indices']
    planes=[plane_from_image(s,q) for q in qs];candidates=[]
    for axis in range(3):
        for sign in (-1.,1.):
            moved=s+sign*.35*np.eye(3)[axis]
            first_image=image_source(moved,*planes[target]);differences=[]
            for receiver in r:
                if reflection_point(moved,receiver,*planes[target]) is None:continue
                paths=[reflection_path(moved,receiver,[planes[i] for i in order]) for order in ((a,b),(b,a))]
                paths=[path for path in paths if path is not None]
                if not paths:continue
                first_length=np.linalg.norm(receiver-first_image)
                differences.append(min(abs(first_length-path['length_m'])/v for path in paths))
            candidates.append(dict(source_position_m=moved.tolist(),predicted_median_delay_separation_s=float(np.median(differences)) if differences else 0.,geometrically_valid_receiver_count=len(differences)))
    candidates.sort(key=lambda x:-x['predicted_median_delay_separation_s'])
    winner=candidates[0]
    return dict(action='move_source_for_reflection_order_discrimination',
        suggested_source_position_m=winner['source_position_m'],
        predicted_median_delay_separation_s=winner['predicted_median_delay_separation_s'],
        receiver_only_discrimination_possible=False if explanation['image_source_difference_m']<=1e-5 else None,
        candidates=candidates,requires='New source pose/configuration calibration and a new session; same coordinate frame.',
        reason='Exactly coincident first-order and double-bounce image sources give identical delays at every receiver for the current fixed source.',
        limitation='Conditional geometric prediction; source directivity, finite extent, occlusion and audibility are not established.')

def _run(session,observations,cancel,progress,method):
    start=time.perf_counter();out=_empty(session,method)
    try:
        _check(cancel);prepared=_prepare(session,observations,out)
        if prepared is None:
            _check(cancel);return out
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
                _check(cancel)
                if any(np.linalg.norm(q-old)<.05 for old in qs):continue
                score,assign,meta=_score(qs+[q],s,r,v,rows,session)
                if score<best-2.0:
                    winner=(q,score)
                    best=score
            if winner is None:break
            qs.append(winner[0])
        if not qs:
            out['diagnostics'].append('no_confirmed_model_beats_null');out['score']=dict(null=null,selected=null)
            candidates=[]
            for q in refined:
                _check(cancel)
                cs,ca,cm=_score([q],s,r,v,rows,session,required_support=4)
                if cm is not None and cs<null-2:
                    candidates.append(_surface(q,0,ca,cm[0],s,r,v,rows,session))
                if len(candidates)>=8:break
            if candidates:
                out['status']='ambiguous'
                out['hypotheses'].append(dict(hypothesis_id='unconfirmed_candidates',surfaces=candidates,reason='Fewer than seven independent confirmations; potentially accidental echo correspondence.'))
                out['guidance'].append(dict(action='Acquire more independent surveyed receiver placements, including height variation.',suggested_position_m=(r.mean(axis=0)+np.array([.35,-.25,.6])).tolist()))
            _check(cancel);return out
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
            _check(cancel)
            if any(np.linalg.norm(q-old)<.15 for old in qs):continue
            cs,ca,cm=_score([q],s,r,v,rows,session,required_support=4)
            if cm is not None and cs<null-2:
                candidate=_surface(q,0,ca,cm[0],s,r,v,rows,session)
                candidates.append(candidate)
            if len(candidates)>=8:break
        if candidates:
            out['hypotheses'].append(dict(hypothesis_id='unconfirmed_candidates',surfaces=candidates,reason='Alternative individual fits; not independent resolved structure. Candidate evidence may overlap other hypotheses.'))
        higher_order=_second_order_explanations(qs,assign,pcov,s,r,v,rows,session,cancel)
        if higher_order and out['surfaces']:
            all_surfaces=out['surfaces'];uncertain={item['target_index'] for item in higher_order}
            for item in higher_order:
                item['target_surface_id']=all_surfaces[item['target_index']]['surface_id']
                item['parent_surface_ids']=[all_surfaces[k]['surface_id'] for k in item['parent_indices']]
            out['higher_order_explanations']=higher_order
            out['hypotheses'].append(dict(hypothesis_id='first_order_reflector_interpretation',surfaces=all_surfaces,reason='A genuine reflector remains possible, including one coincident with a double-bounce image.'))
            out['hypotheses'].append(dict(hypothesis_id='fewer_surfaces_with_second_order_paths',surfaces=[surface for k,surface in enumerate(all_surfaces) if k not in uncertain],higher_order_explanations=higher_order,reason='Physically admissible double-bounce paths explain these additional images without asserting extra physical planes. Unknown finite extents and occlusion remain.'))
            # Retain selected surfaces until all independent ambiguity checks
            # have run; higher-order ambiguity must not hide mirror/rank evidence.
            out['status']='ambiguous'
            out['diagnostics'].append('first_order_vs_higher_order_ambiguity')
            out['guidance'].append(_source_discrimination_guidance(higher_order[0],qs,s,r,v))
        # Receiver-only coplanarity is sufficient for fixed-source image mirror
        # symmetry. Each surface must be checked against its own supporting views;
        # an elevated receiver with no matched echo cannot resolve that ambiguity.
        ambiguous=[];mirrors=[];unique=[]
        origins={p['surface_id']:i for i,p in enumerate(out['surfaces'])}
        rank_ambiguous=[]
        for k,surface in enumerate(out['surfaces']):
            if surface['uncertainty']['rank_deficient']:
                rank_ambiguous.append(surface);continue
            indices=[i for ki,i,l in assign if ki==k]
            supporting=r[indices];center=supporting.mean(axis=0)
            _,singular,Vh=np.linalg.svd(supporting-center,full_matrices=False)
            if singular[-1]<1e-5:
                mirror_normal=Vh[-1];qm=qs[k]-2*np.dot(qs[k]-center,mirror_normal)*mirror_normal
                nm,dm=plane_from_image(s,qm)
                admissible=all(reflection_point(s,ri,nm,dm) is not None for ri in supporting)
                if np.linalg.norm(qs[k]-qm)>.05 and admissible:
                    ambiguous.append(surface);mirrors.append(qm);continue
            unique.append(surface)
        if rank_ambiguous:
            out['status']='ambiguous'
            out['diagnostics'].append('local_geometry_rank_deficient')
            out['hypotheses'].append(dict(hypothesis_id='rank_deficient_candidates',surfaces=rank_ambiguous,reason='Local Gaussian orientation uncertainty is not observable from these supporting positions.'))
        if ambiguous or rank_ambiguous:
            out['status']='ambiguous';out['diagnostics'].append('support_coplanar_mirror_ambiguity')
            primary=[surface['image_source_m'] for surface in ambiguous]
            out['hypotheses']=[dict(hypothesis_id='primary',surfaces=ambiguous,image_sources_m=primary),
                dict(hypothesis_id='coplanar_mirror',image_sources_m=[q.tolist() for q in mirrors],planes=[dict(normal=plane_from_image(s,q)[0].tolist(),offset_m=plane_from_image(s,q)[1]) for q in mirrors])]+out['hypotheses']
            if unique:
                out['hypotheses'].append(dict(hypothesis_id='invariant_supported_surfaces',surfaces=unique,reason='These planes are invariant under tested mirror alternatives, but the scene remains globally ambiguous.'))
            out['surfaces']=[]
            pose_candidates=[(r[0]+sign*.8*np.eye(3)[axis]).tolist() for axis in range(3) for sign in (-1,1)]
            recommendation=recommend_next_view(session,out,pose_candidates)
            out['guidance'].append(dict(action='Change receiver height or move out of the support plane and survey its new position.',**recommendation,reason='Same-plane additional captures cannot remove a global mirror ambiguity. Missing echoes do not resolve it.'))
        if higher_order:
            out['surfaces']=[]
        for a,b in combinations(range(len(out['surfaces'])),2):
            pa,pb=out['surfaces'][a],out['surfaces'][b];ia,ib=origins[pa['surface_id']],origins[pb['surface_id']];na=np.array(pa['normal']);nb=np.array(pb['normal']);dot=float(na@nb)
            if abs(dot)>np.cos(np.deg2rad(3)) and out['status']!='ambiguous':
                sep,direction,points,reference_gradient=_local_plane_intersections(s,qs[ia],qs[ib])
                grad=np.zeros(3*len(qs));eps=1e-5
                for pair_index,idx in enumerate((ia,ib)):
                    for axis in range(3):
                        plus=[qs[ia].copy(),qs[ib].copy()];minus=[qs[ia].copy(),qs[ib].copy()]
                        plus[pair_index][axis]+=eps;minus[pair_index][axis]-=eps
                        grad[3*idx+axis]=(_local_plane_intersections(s,*plus)[0]-_local_plane_intersections(s,*minus)[0])/(2*eps)
                geometry_std=float(np.sqrt(max(0,grad@pcov@grad)))
                reference_std=float(np.sqrt(max(0,reference_gradient@_calibration_covariance(session,v)[:3,:3]@reference_gradient)))
                # Fitted plane geometry and reference pose share calibration
                # errors. Their cross-covariance is not retained separately:
                # sum marginal standard deviations to bound any correlation.
                sepstd=geometry_std+reference_std
                out['dimensions'].append(dict(kind='local_plane_intersection_separation',surface_ids=[pa['surface_id'],pb['surface_id']],value_m=float(sep),std_m=sepstd,geometry_std_m=geometry_std,reference_std_bound_m=reference_std,reference_point_m=s.tolist(),reference_kind='surveyed_source_acoustic_center',direction=direction.tolist(),intersection_points_m=points.tolist(),normal_angle_rad=float(np.arccos(np.clip(abs(dot),0,1))),semantics='Distance between intersections along the mean-normal line through the stated source reference. Nonparallel planes have no unique global separation; this is not a proven room dimension.',uncertainty_kind='first_order_conservative_standard_deviation_bound',uncertainty_note='Joint plane covariance includes shared calibration. Add the reference-location standard-deviation contribution conservatively because reference/geometry cross-covariance is not separately retained; do not interpret as a calibrated confidence interval.'))
        if not out['guidance']:out['guidance'].append(dict(action='Add surveyed views around weakly supported reflectors with a different height.',suggested_position_m=(r.mean(axis=0)+np.array([.35,-.25,.6])).tolist(),reason='Finite support and missing echoes do not establish physical edges or empty space.'))
        out['provenance']=sorted(set(o.get('provenance','unspecified') for o in observations))
        out['search']['complete']=not any('budget' in str(x) or 'limit' in str(x) for x in out['diagnostics'])
        out['search']['global_optimality_proven']=False
        if not out['search']['complete'] and out['status']=='ok':out['status']='partial'
        if progress:progress(1.,'Inference complete')
        _check(cancel)
        return out
    except _Cancelled:
        # A fit is assembled before its ambiguity checks finish. Never publish
        # those intermediate objects as definitive or qualified hypotheses.
        for key in ('surfaces','hypotheses','dimensions','guidance'):out[key]=[]
        for key in ('shared_image_source_covariance_m2','higher_order_explanations','score'):out.pop(key,None)
        out['search']['complete']=False
        out['status']='cancelled';out['diagnostics'].append('cancelled_by_caller');return out
    finally:
        out['runtime_s']=time.perf_counter()-start


def infer_scene(session, observations, cancel=None, progress=None):
    return _run(session,observations,cancel,progress,'image_source_consensus')


def infer_baseline(session, observations, cancel=None, progress=None):
    """Independent direct-plane grid initializer, identical observations/scoring."""
    return _run(session,observations,cancel,progress,'direct_plane_grid_baseline')


def infer_first_echo(session, observations, cancel=None, progress=None):
    """Simple earliest-echo baseline with the correct bistatic forward model.

    One candidate per receiver assumes the first returned echo belongs to the
    same reflector across views. That assumption frequently fails in rooms.
    """
    filtered=[dict(o,candidates=sorted(o.get('candidates',[]),key=lambda p:p['delay_s'])[:1]) for o in observations]
    out=_run(session,filtered,cancel,progress,'image_source_consensus')
    out['method']='earliest_echo_bistatic_baseline'
    out['assumptions'].append('earliest detected echo correspondence across receivers')
    return out


def recommend_next_view(session, result, candidate_positions_m):
    """Rank supplied surveyed placement options by ambiguity separation.

    Does not consult scene truth or infer whether a location is accessible or
    a reflector is audible. Positions are proposals for the operator to survey.
    """
    s=np.asarray(session['source_position_m'],float)
    v=_effective_speed(session)
    calibration_covariance=_calibration_covariance(session,v)
    rstd=.01;timing=5e-5
    groups=[h['image_sources_m'] for h in result.get('hypotheses',[]) if h.get('image_sources_m')]
    pairs=[]
    if len(groups)>=2:
        pairs=[(np.asarray(a),np.asarray(b)) for a,b in zip(groups[0],groups[1]) if np.linalg.norm(np.asarray(a)-b)>.05]
    ranked=[]
    for position in candidate_positions_m:
        r=np.asarray(position,float)
        if r.shape!=(3,) or not np.all(np.isfinite(r)) or np.linalg.norm(r-s)<.05:continue
        separation=[];details=[]
        for qa,qb in pairs:
            values=[];gr=[];gs=[]
            for q in (qa,qb):
                n,d=plane_from_image(s,q)
                if reflection_point(s,r,n,d) is None:break
                u=(r-s)/np.linalg.norm(r-s);g=(r-q)/np.linalg.norm(r-q)
                values.append(float(excess_delay(s,r,q,v)))
                gr.append((g-u)/v);gs.append((u-(np.eye(3)-2*np.outer(n,n))@g)/v)
            if len(values)!=2:continue
            difference=abs(values[0]-values[1])
            calibration_gradient=np.r_[gs[0]-gs[1],-(values[0]-values[1])/v]
            variance=2*timing**2+float(calibration_gradient@calibration_covariance@calibration_gradient)+rstd**2*float(np.sum((gr[0]-gr[1])**2))
            sigma=np.sqrt(variance);separation.append(difference/sigma)
            details.append(dict(delay_separation_s=difference,conditional_std_s=float(sigma)))
        score=min(separation) if separation else 0.
        ranked.append(dict(position_m=r.tolist(),score_sigma=float(score),predicted_differences=details))
    ranked.sort(key=lambda item:-item['score_sigma'])
    if not ranked:return dict(status='no_valid_candidate_positions',candidates=[])
    return dict(status='predicted_ambiguity_separation' if pairs else 'no_competing_geometric_hypotheses',
                suggested_position_m=ranked[0]['position_m'],score_sigma=ranked[0]['score_sigma'],candidates=ranked,
                uncertainty_semantics='Shared calibration terms propagated through hypothesis difference; conditional on point-source specular model.',
                limitation='Prediction does not establish audibility, accessibility, or guaranteed resolution.')
