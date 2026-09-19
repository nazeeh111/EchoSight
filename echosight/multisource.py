"""Joint first-order plane inference from recordings at several source poses.

Source relocation constrains a common physical plane, rather than averaging
single-source output. Conditional Gaussian covariance retains the declared joint
source/speed calibration and reused receiver survey errors exactly once.
"""
from pathlib import Path
from itertools import permutations
import hashlib
import json
import time
import numpy as np
from scipy.optimize import least_squares, linear_sum_assignment
from . import inference as single
from .receiver_covariance import validate as _receiver_calibration, project as _receiver_projection, marginal as _receiver_marginal, describe as _receiver_description
from .geometry import plane_from_image, image_source, reflection_point, support_mesh, reflection_path

MAX_SOURCES = 4
MAX_RECORDS = 64
MAX_PLANES = 10


def _empty(bundle, method):
    bundle=bundle if isinstance(bundle,dict) else {}
    return dict(schema_version='1.0', scene_id=bundle.get('scene_id'),
        coordinate_frame_id=bundle.get('coordinate_frame_id'), status='no_result',
        method='multi_source_'+method, surfaces=[], hypotheses=[], diagnostics=[],
        guidance=[], dimensions=[], processed_sessions=[],
        assumptions=['static scene in a shared surveyed frame', 'one calibrated point emitter per source pose',
                     'candidate planes are conditional first-order interpretations'],
        uncertainty_semantics='Conditional local covariance; reflection order, source directivity, and unmodeled waveform bias are excluded.')


def _psd(value, size):
    a=np.asarray(value,float)
    if a.shape!=(size,size) or not np.isfinite(a).all() or not np.allclose(a,a.T,rtol=1e-8,atol=1e-12):
        raise ValueError('invalid shared covariance shape, values, or symmetry')
    a=(a+a.T)/2
    if np.linalg.eigvalsh(a).min() < -1e-12:raise ValueError('shared covariance is not positive semidefinite')
    return a


def _calibration(bundle, count):
    c=bundle['shared_calibration'];v=float(c['effective_speed_m_s'])
    if not np.isfinite(v) or not 250<=v<=460:raise ValueError('invalid effective speed')
    if 'joint_source_effective_speed_covariance' in c:
        cov=_psd(c['joint_source_effective_speed_covariance'],3*count+1)
    elif c.get('covariance_assumption')=='explicit_source_pose_covariance_independent_speed':
        cov=np.zeros((3*count+1,3*count+1))
        cov[:-1,:-1]=_psd(c['source_pose_joint_covariance_m2'],3*count)
        std=float(c['effective_speed_std_m_s'])
        if not np.isfinite(std) or std<0:raise ValueError('invalid effective speed uncertainty')
        cov[-1,-1]=std*std
    else:raise ValueError('explicit joint calibration covariance is required')
    return v,cov


def _predict(q, reference, sources, receivers, v):
    n,d=plane_from_image(reference,q)
    images=sources+2*(d-sources@n)[:,None]*n
    mu=(np.linalg.norm(receivers-images,axis=1)-np.linalg.norm(receivers-sources,axis=1))/v
    valid=((sources@n-d)*(receivers@n-d)>1e-8)&(mu>0)&(mu<.12)
    return mu,valid


def _nearest(q, reference, sources, receivers, v, rows):
    mu,valid=_predict(q,reference,sources,receivers,v)
    ids=np.array([np.argmin(abs(row['t']-m)) for row,m in zip(rows,mu)])
    residual=np.array([row['t'][j]-m for row,j,m in zip(rows,ids,mu)])*v
    return ids,residual,valid&(abs(residual)<single.GATE_M)


def _refine(q, reference, sources, receivers, v, rows):
    for _ in range(3):
        ids,e,good=_nearest(q,reference,sources,receivers,v,rows)
        if good.sum()<8:return None
        target=np.array([row['t'][j] for row,j in zip(rows,ids)])
        fit=least_squares(lambda x:(_predict(x,reference,sources[good],receivers[good],v)[0]-target[good])*v,
                          q,loss='soft_l1',f_scale=.02,max_nfev=35)
        if np.linalg.norm(q-fit.x)<1e-7:q=fit.x;break
        q=fit.x
    return q


def _assign(qs,reference,sources,receivers,v,rows):
    links=[];cost=single.PLANE_COST*len(qs)
    predictions=[_predict(q,reference,sources,receivers,v) for q in qs]
    for i,row in enumerate(rows):
        k=len(qs);m=len(row['t']);c=np.full((k,m+k),1e9)
        for j,(mu,valid) in enumerate(predictions):
            c[j,m+j]=single.MISS_COST if valid[i] else 0
            if valid[i]:
                e=(row['t']-mu[i])*v
                c[j,:m]=np.where(abs(e)<single.GATE_M,.5*(e/.025)**2-single.CLUTTER_COST,1e9)
        a,b=linear_sum_assignment(c)
        cost+=float(c[a,b].sum())
        links.extend((int(j),i,int(l)) for j,l in zip(a,b) if l<m)
    return cost,links


def _supported(links,rows,count):
    for k in range(count):
        subset=[i for p,i,l in links if p==k]
        bysource=[sum(rows[i]['source_index']==a for i in subset) for a in set(row['source_index'] for row in rows)]
        if any(n<4 for n in bysource) or len(subset)<8:return False
        points=np.array([rows[i]['r'] for i in subset])
        if np.linalg.matrix_rank(points-points.mean(axis=0),tol=1e-5)<3:return False
    return True


def _covariance(qs,reference,sources,receivers,v,rows,links,calibration_covariance,receiver_calibration=None):
    """Derivatives in seconds; all nuisance covariance added once before inversion."""
    m=len(links);J=np.zeros((m,3*len(qs)));A=np.zeros((m,len(calibration_covariance)))
    C=np.zeros((m,m));receiver_grad=[];res=[];pred=[]
    for a,(k,i,l) in enumerate(links):
        row=rows[i];s=sources[i];r=receivers[i];n,d=plane_from_image(reference,qs[k]);q=image_source(s,n,d)
        u=(q-r)/np.linalg.norm(q-r);u0=(s-r)/np.linalg.norm(s-r)
        mu=(np.linalg.norm(q-r)-np.linalg.norm(s-r))/v
        for axis in range(3):
            h=np.eye(3)[axis]*1e-5
            J[a,3*k+axis]=(_predict(qs[k]+h,reference,s[None],r[None],v)[0][0]-_predict(qs[k]-h,reference,s[None],r[None],v)[0][0])/(2e-5)
        A[a,3*row['source_index']:3*row['source_index']+3]=(u@(np.eye(3)-2*np.outer(n,n))-u0)/v
        A[a,-1]=-mu/v
        receiver_grad.append((u0-u)/v);pred.append(mu);res.append(row['t'][l]-mu)
        C[a,a]=max(float(row['peaks'][l].get('delay_std_s',1e-5)),1e-7)**2
    C+=A@calibration_covariance@A.T
    C+=_receiver_projection([rows[i]['receiver_group'] for _,i,_ in links],receiver_grad,
                            [rows[i]['o'].get('receiver_position_std_m',.01) for _,i,_ in links],receiver_calibration)
    for a,(_,i,l) in enumerate(links):
        for b,(_,j,ll) in enumerate(links):
            if i==j:
                o=rows[i]['o'];clock=o.get('clock',{})
                C[a,b]+=o.get('direct_std_s',1e-5)**2
                C[a,b]+=pred[a]*pred[b]*(clock.get('alpha_std',0)/clock.get('alpha',1))**2
    # The final estimator is ordinary least squares. Its covariance is the
    # sandwich propagation L C L.T, not the smaller GLS covariance of an
    # estimator we did not execute. Shared errors must survive averaging.
    rank=np.linalg.matrix_rank(J);influence=np.linalg.pinv(J)
    covariance=influence@C@influence.T
    standardized=float(np.array(res)@np.linalg.solve(C,np.array(res)))
    covariance*=max(1.,standardized/max(1,m-rank))
    return covariance,rank,standardized




def _physical_path_groups(residual,observed_delays,links):
    """One capacity per coincident predicted arrival in each recording.

    Different reflection labels with the same travel time cannot supply two
    distinct detected peaks. The 1 ns tolerance groups numerical coincidences;
    it does not merge paths at the much larger detector resolution scale.
    """
    captures={}
    for row,(k,i,l) in enumerate(links):captures.setdefault(i,[]).append(row)
    groups=[]
    for indices in captures.values():
        indices=np.array(indices);prediction=observed_delays[indices[0]]-residual[indices[0]]
        ordered=np.argsort(prediction);ids=np.empty(len(prediction),dtype=int);group=-1;previous=None
        for col in ordered:
            if previous is None or abs(prediction[col]-previous)>1e-9:group+=1
            ids[col]=group;previous=prediction[col]
        groups.append((indices,ids))
    return groups


def _exclusive_physical_assignment(cost,groups,allowed,cancel=None,maximum_score=np.inf):
    """Assign distinct selected peaks to distinct physical-arrival groups."""
    columns=np.flatnonzero(allowed);choices=np.full(cost.shape[0],-1,dtype=int);score=0.
    for indices,path_groups in groups:
        single._check(cancel)
        ids,inverse=np.unique(path_groups[columns],return_inverse=True)
        if len(ids)<len(indices):return None
        edges=cost[np.ix_(indices,columns)]
        grouped=np.full((len(ids),len(indices)),np.inf)
        np.minimum.at(grouped,inverse,edges.T)
        try:row_ids,group_ids=linear_sum_assignment(grouped.T)
        except ValueError:return None
        assigned=grouped[group_ids,row_ids]
        if not np.all(np.isfinite(assigned)):return None
        score+=float(assigned.sum())
        if score>maximum_score:return None
        for local_row,chosen_group in zip(row_ids,group_ids):
            members=np.where(inverse==chosen_group)[0]
            selected=members[np.argmin(edges[local_row,members])]
            choices[indices[local_row]]=columns[selected]
    return score,choices


def _parent_subset_alternatives(out,qs,reference,sources,receivers,v,rows,links,calibration_covariance,parameter_covariance,cancel,receiver_calibration=None):
    """Bounded physical explanations on fixed evidence, not model probabilities.

    The engineering rule was declared in work/multisource-discrimination/RULE.md:
    preserve sufficient competing parent subsets; never infer reflector absence.
    """
    count=len(qs)
    if count<3 or not out['surfaces']:return
    planes=[plane_from_image(reference,q) for q in qs]
    paths=[(i,) for i in range(count)]+list(permutations(range(count),2))
    masks=np.array([sum(1<<i for i in set(path)) for path in paths])
    indices=np.array([i for k,i,l in links]);source_indices=np.array([rows[i]['source_index'] for i in indices])
    src=sources[indices];rec=receivers[indices];ys=np.array([rows[i]['t'][l] for k,i,l in links])
    independent=np.array([rows[i]['peaks'][l].get('delay_std_s',1e-5)**2+rows[i]['o'].get('direct_std_s',1e-5)**2 for k,i,l in links])
    residual=np.full((len(links),len(paths)),np.inf);compatible=np.zeros_like(residual,dtype=bool)
    def prediction(path,parameters):
        images=src.copy()
        for parent in path:
            n,d=plane_from_image(reference,parameters[parent]);images=images+2*(d-images@n)[:,None]*n
        return (np.linalg.norm(images-rec,axis=1)-np.linalg.norm(src-rec,axis=1))/v,images
    for col,path in enumerate(paths):
        single._check(cancel)
        mu,images=prediction(path,qs)
        if len(path)==1:
            n,d=planes[path[0]];valid=(src@n-d)*(rec@n-d)>1e-8
        else:
            valid=np.array([reflection_path(s,r,[planes[p] for p in path]) is not None for s,r in zip(src,rec)])
        u=(images-rec)/np.linalg.norm(images-rec,axis=1)[:,None];u0=(src-rec)/np.linalg.norm(src-rec,axis=1)[:,None]
        transform=np.eye(3)
        for p in path:
            n,d=planes[p];transform=(np.eye(3)-2*np.outer(n,n))@transform
        source_gradient=(u@transform-u0)/v;receiver_gradient=(u0-u)/v
        A=np.zeros((len(links),len(calibration_covariance)))
        for row,a in enumerate(source_indices):A[row,3*a:3*a+3]=source_gradient[row]
        A[:,-1]=-mu/v
        variance=independent+np.einsum('ij,jk,ik->i',A,calibration_covariance,A)
        variance+=_receiver_marginal([rows[i].get('receiver_group') for i in indices],receiver_gradient,
                                    [rows[i]['o'].get('receiver_position_std_m',.01) for i in indices],receiver_calibration)
        for row,i in enumerate(indices):
            o=rows[i]['o'];clock=o.get('clock',{})
            variance[row]+=mu[row]**2*(clock.get('alpha_std',0)/clock.get('alpha',1))**2
        J=np.zeros((len(links),3*count))
        for parent in path:
            for axis in range(3):
                plus=[q.copy() for q in qs];minus=[q.copy() for q in qs];plus[parent][axis]+=1e-5;minus[parent][axis]-=1e-5
                J[:,3*parent+axis]=(prediction(path,plus)[0]-prediction(path,minus)[0])/(2e-5)
        # Parent geometry and calibration share uncertainty; adding marginal
        # standard deviations bounds unknown cross-correlation conservatively.
        parent_variance=np.einsum('ij,jk,ik->i',J,parameter_covariance,J)
        tolerance=3*(np.sqrt(np.maximum(variance,1e-14))+np.sqrt(np.maximum(parent_variance,0)))
        error=ys-mu;residual[:,col]=error
        compatible[:,col]=valid&(abs(error)<=tolerance)
    original=np.array([residual[row,k] for row,(k,i,l) in enumerate(links)])
    denominator=np.maximum(independent,1e-14)
    original_score=float(np.sum(original**2/denominator));sufficient=[]
    path_groups=_physical_path_groups(residual,ys,links)
    comparison_cost=np.where(compatible,residual**2/denominator[:,None],np.inf)
    tolerance_score=original_score+1e-8*(1+original_score)
    for mask in range(1,(1<<count)-1):
        if mask%16==0:single._check(cancel)
        allowed=(masks&mask)==masks
        assignment=_exclusive_physical_assignment(comparison_cost,path_groups,allowed,cancel,tolerance_score)
        if assignment is None:continue
        score,choices=assignment
        sufficient.append(dict(parent_indices=[i for i in range(count) if mask&(1<<i)],score=score))
    if not sufficient:return
    sufficient.sort(key=lambda x:(len(x['parent_indices']),x['score']))
    invariant=set(range(count))
    for model in sufficient:invariant.intersection_update(model['parent_indices'])
    all_surfaces=out['surfaces'];best=sufficient[0];kept=best['parent_indices']
    out['hypotheses'].append(dict(hypothesis_id='joint_first_order_interpretation',surfaces=all_surfaces,reason='Additional physical reflectors remain possible.'))
    out['hypotheses'].append(dict(hypothesis_id='joint_fewer_parents_with_second_order_paths',surfaces=[all_surfaces[i] for i in kept],parent_indices=kept,score=best['score'],reason='These fixed parent planes explain the same selected recording candidates with physically valid first- or second-order paths. Extra planes are not required by this explanation; their absence is not established.'))
    best_mask=sum(1<<i for i in kept);allowed=(masks&best_mask)==masks
    _,choices=_exclusive_physical_assignment(comparison_cost,path_groups,allowed,cancel,tolerance_score)
    path_evidence=[]
    for row,((k,i,l),choice) in enumerate(zip(links,choices)):
        path=paths[choice];observation=rows[i]
        path_evidence.append(dict(session_id=observation['session_id'],capture_id=observation['o']['capture_id'],candidate_id=observation['peaks'][l]['candidate_id'],reflection_order=len(path),parent_surface_ids=[all_surfaces[p]['surface_id'] for p in path],observed_delay_s=float(ys[row]),predicted_delay_s=float(ys[row]-residual[row,choice]),residual_s=float(residual[row,choice]),extent_and_occlusion_status='unknown'))
    out['hypotheses'][-1]['path_evidence']=path_evidence
    out['parent_model_comparison']=dict(original_score=original_score,score_semantics='Squared residuals on fixed selected evidence, normalized by fixed marginal detector/direct timing scale; not likelihood, chi-square significance, or posterior.',compatibility_semantics='Three marginal standard deviations with declared calibration, receiver, clock and conservative fitted-parent uncertainty; selection effects are not calibrated.',assignment_semantics='Exclusive candidate-to-predicted-arrival matching within each recording; coincident path predictions share one capacity.',coincident_arrival_tolerance_s=1e-9,enumerated_subsets=(1<<count)-1,sufficient_alternatives=sufficient,invariant_parent_indices=sorted(invariant),parent_surface_ids=[p['surface_id'] for p in all_surfaces],extent_and_occlusion_status='unknown',absence_established=False)
    out['surfaces']=[all_surfaces[i] for i in sorted(invariant)]
    for surface in out['surfaces']:surface['model_status']='invariant_across_tested_parent_subsets_conditional_on_path_model'
    out['status']='partial' if out['surfaces'] else 'ambiguous'
    out['diagnostics'].append('joint_first_order_vs_second_order_parent_models')
    out['guidance'].append(dict(action='Acquire source/receiver views with larger predicted separation between the retained physical path explanations.',requires='Surveyed source acoustic centers and unchanged calibrated source configuration; confirm accessibility and audibility.',limitation='Finite extent, occlusion and reflector absence are not established.'))


def infer_scene_bundle(processed_sessions,bundle,method='mapper',cancel=None,progress=None):
    start=time.perf_counter();out=_empty(bundle,method);out['processed_sessions']=processed_sessions
    try:
        if not isinstance(bundle,dict):raise ValueError('bundle must be an object')
        if bundle.get('schema_version','1.0')!='1.0':raise ValueError('unsupported bundle schema_version')
        if not isinstance(processed_sessions,list):raise ValueError('processed_sessions must be an array')
        if method not in ('mapper','plane_grid'):raise ValueError('unknown joint method')
        single._check(cancel)
        count=len(processed_sessions)
        if not 2<=count<=MAX_SOURCES:raise ValueError('requires two to four source sessions')
        if bundle.get('scene_static') is not True or not bundle.get('coordinate_frame_id'):raise ValueError('static common coordinate frame must be declared')
        v,calcov=_calibration(bundle,count)
        receiver_calibration=_receiver_calibration(bundle,processed_sessions,cancel)
        out['receiver_pose_uncertainty']=_receiver_description(receiver_calibration)
        allrows=[];sources_list=[];prepared=[];groups={};session_ids=set()
        for a,item in enumerate(processed_sessions):
            session=item['session'];observations=item['observations']
            sid=session.get('session_id')
            if not isinstance(sid,str) or not sid:raise ValueError('source session_id must be a nonempty string')
            if sid in session_ids:raise ValueError('duplicate source session_id')
            session_ids.add(sid)
            if session.get('coordinate_frame_id')!=bundle['coordinate_frame_id']:raise ValueError('coordinate_frame_mismatch')
            cov=calcov[np.ix_([3*a,3*a+1,3*a+2,3*count],[3*a,3*a+1,3*a+2,3*count])]
            session=dict(session,effective_speed_m_s=v,source_effective_speed_covariance=cov.tolist())
            diagnostic=single._empty(session,method);p=single._prepare(session,observations,diagnostic)
            if p is None:raise ValueError('source session lacks independent usable receiver observations')
            s,_,rows,r=p;prepared.append((session,s,rows,r));sources_list.append(s)
            captures={c['capture_id']:c for c in session.get('captures',[])}
            for row in rows:
                o=row['o'];capture=captures.get(o['capture_id'],{})
                group=o.get('receiver_pose_group_id',capture.get('receiver_pose_group_id'))
                if not isinstance(group,str) or not 1<=len(group)<=160:raise ValueError('receiver_pose_group_id must be a string of 1 to 160 characters')
                stamp=(row['r'],o.get('receiver_position_std_m',.01) if receiver_calibration is None else None)
                if group in groups and (not np.allclose(groups[group][0],stamp[0],atol=1e-8,rtol=0) or groups[group][1]!=stamp[1]):raise ValueError('reused receiver pose group has inconsistent survey')
                groups[group]=stamp;row.update(source_index=a,receiver_group=group,session_id=session['session_id']);allrows.append(row)
        if len(allrows)>MAX_RECORDS:raise ValueError('joint capture resource limit exceeded')
        reference=sources_list[0];sources=np.array([sources_list[row['source_index']] for row in allrows]);receivers=np.array([row['r'] for row in allrows])
        seeds=[]
        for a,(session,s,rows,r) in enumerate(prepared):
            single._check(cancel)
            dummy=single._empty(session,method)
            proposals=single._proposals(s,r,v,rows,'image_source_consensus' if method=='mapper' else 'direct_plane_grid_baseline',cancel,dummy)
            ranked=single._rank_proposals(proposals,s,r,v,rows,cancel)
            for q in ranked:
                n,d=plane_from_image(s,q);candidate=image_source(reference,n,d)
                if all(np.linalg.norm(candidate-old)>.05 for old in seeds):seeds.append(candidate)
            if progress:progress(.2+.3*(a+1)/count,'Generating cross-source plane candidates')
        ranked=[]
        for q in seeds:
            ids,e,good=_nearest(q,reference,sources,receivers,v,allrows)
            rank=-good.sum()+.25*np.sum((e[good]/.025)**2)
            ranked.append((rank,q))
        refined=[]
        for _,q in sorted(ranked,key=lambda x:x[0])[:96]:
            single._check(cancel);fit=_refine(q,reference,sources,receivers,v,allrows)
            if fit is not None and all(np.linalg.norm(fit-old)>.06 for old in refined):refined.append(fit)
        qs=[];best=0.
        for _ in range(MAX_PLANES):
            winner=None
            for q in refined:
                single._check(cancel)
                if any(np.linalg.norm(q-old)<.06 for old in qs):continue
                score,links=_assign(qs+[q],reference,sources,receivers,v,allrows)
                if score<best-2 and _supported(links,allrows,len(qs)+1):winner=q;best=score
            if winner is None:break
            qs.append(winner)
        if not qs:out['diagnostics'].append('no_joint_plane_beats_null');return out
        # Refit the complete model to its exclusive assignments; proposals
        # alone used a robust loss. Freeze links for covariance propagation.
        for _ in range(2):
            score,links=_assign(qs,reference,sources,receivers,v,allrows)
            for k,q in enumerate(qs):
                selected=[(i,l) for kk,i,l in links if kk==k]
                indices=np.array([i for i,l in selected]);target=np.array([allrows[i]['t'][l] for i,l in selected])
                fit=least_squares(lambda x:(_predict(x,reference,sources[indices],receivers[indices],v)[0]-target)*v,q,max_nfev=35)
                qs[k]=fit.x
        score,links=_assign(qs,reference,sources,receivers,v,allrows)
        if not _supported(links,allrows,len(qs)):
            out['diagnostics'].append('joint_refit_lost_required_support');return out
        pcov,rank,chi2=_covariance(qs,reference,sources,receivers,v,allrows,links,calcov,receiver_calibration)
        surfaces=[]
        for k,q in enumerate(qs):
            n,d=plane_from_image(reference,q);evidence=[];points=[]
            for kk,i,l in links:
                if kk!=k:continue
                row=allrows[i];mu=_predict(q,reference,sources[i:i+1],receivers[i:i+1],v)[0][0]
                point=reflection_point(sources[i],receivers[i],n,d)
                if point is not None:points.append(point)
                evidence.append(dict(session_id=row['session_id'],capture_id=row['o']['capture_id'],candidate_id=row['peaks'][l]['candidate_id'],delay_s=float(row['t'][l]),predicted_delay_s=float(mu),residual_s=float(row['t'][l]-mu),source_position_m=sources[i].tolist(),receiver_pose_group_id=row['receiver_group']))
            vertices,triangles=support_mesh(points,n);jac=np.zeros((4,3))
            for axis in range(3):
                h=np.eye(3)[axis]*1e-5;np_,dp=plane_from_image(reference,q+h);nm,dm=plane_from_image(reference,q-h)
                if np_@n<0:np_,dp=-np_,-dp
                if nm@n<0:nm,dm=-nm,-dm
                jac[:,axis]=(np.r_[np_,dp]-np.r_[nm,dm])/(2e-5)
            cov=jac@pcov[3*k:3*k+3,3*k:3*k+3]@jac.T
            sid=hashlib.sha256(json.dumps(evidence,sort_keys=True).encode()).hexdigest()[:16]
            surfaces.append(dict(surface_id='reflector-'+sid,kind='unclassified_planar_reflector',model_status='conditional_first_order_hypothesis',normal=n.tolist(),offset_m=d,support=evidence,vertices_m=vertices,triangles=triangles,extent_status='unknown',mesh_semantics='reflection_support_convex_hull_not_physical_edges',uncertainty=dict(offset_std_m=float(np.sqrt(max(0,cov[3,3]))),normal_angular_std_rad=float(np.sqrt(max(0,np.trace(cov[:3,:3])))),conditional_on='joint associations and common first-order point-source model'),confidence=dict(kind='evidence_summary_not_probability',supporting_views=len(evidence),supporting_source_poses=len(set(e['session_id'] for e in evidence)),rms_residual_m=float(v*np.sqrt(np.mean([e['residual_s']**2 for e in evidence]))))))
        source_rank=np.linalg.matrix_rank(np.array(sources_list)-np.mean(sources_list,axis=0),tol=.03)
        out.update(surfaces=surfaces,status='partial',shared_plane_parameter_covariance_m2=pcov.tolist(),source_diversity_rank=int(source_rank),score=dict(selected=score,null=0.,standardized_residual=chi2),search=dict(proposals=len(seeds),refined=min(96,len(ranked)),global_optimality_proven=False))
        if source_rank<3 or rank<3*len(qs):
            out['hypotheses'].append(dict(hypothesis_id='source_motion_ambiguous',surfaces=surfaces,reason='Source movement does not constrain a general source-image transformation; higher-order aliases remain possible.'))
            out['surfaces']=[];out['status']='ambiguous';out['diagnostics'].append('insufficient_source_diversity_for_reflection_order_discrimination')
            out['guidance'].append(dict(action='Acquire source poses spanning three dimensions with recalibrated acoustic center; avoid source poses confined to one line or plane.'))
        if out['surfaces']:
            _parent_subset_alternatives(out,qs,reference,sources,receivers,v,allrows,links,calcov,pcov,cancel,receiver_calibration)
        if out['surfaces']:
            from .path_alternatives import apply_path_alternatives
            apply_path_alternatives(out,processed_sessions,v,calcov,cancel,receiver_calibration=receiver_calibration)
        if progress:progress(1.,'Joint inference complete')
        return out
    except single._Cancelled:
        out['status']='cancelled';out['surfaces']=[];out['diagnostics'].append('cancelled_by_caller');return out
    except (ValueError,KeyError,TypeError,np.linalg.LinAlgError) as exc:
        out['diagnostics'].append(str(exc));out['status']='calibration_needed';out['surfaces']=[]
        for hypothesis in out['hypotheses']:
            hypothesis['verification_status']='unverified_due_to_processing_error'
        return out
    finally:out['runtime_s']=time.perf_counter()-start


def process_scene_bundle(bundle,cancel=None,progress=None,*,method='mapper'):
    """Bounded lossless recording entry; malformed input yields no_result."""
    from .storage import load_session,validate_session,read_recording_evidence_snapshot,reject_reused_waveforms,MAX_JSON_BYTES
    from .signals import process_recording
    start=time.perf_counter();base=Path.cwd();out=_empty(bundle,method);processed=[]
    try:
        single._check(cancel)
        if isinstance(bundle,(str,Path)):
            path=Path(bundle);base=path.parent
            with path.open('rb') as stream:raw=stream.read(MAX_JSON_BYTES+1)
            if len(raw)>MAX_JSON_BYTES:raise ValueError('bundle JSON exceeds byte limit')
            bundle=json.loads(raw)
        if not isinstance(bundle,dict):raise ValueError('bundle must be an object')
        out=_empty(bundle,method)
        if bundle.get('schema_version','1.0')!='1.0':raise ValueError('unsupported bundle schema_version')
        if method not in ('mapper','plane_grid'):raise ValueError('unknown joint method')
        entries=bundle.get('sessions')
        if not isinstance(entries,list):raise ValueError('bundle sessions must be an array')
        if not 2<=len(entries)<=MAX_SOURCES:raise ValueError('requires two to four source sessions')
        _calibration(bundle,len(entries))
        if bundle.get('scene_static') is not True or not bundle.get('coordinate_frame_id'):raise ValueError('static common coordinate frame must be declared')
        sessions=[];session_ids=set();total_records=0
        # Validate all acquisition identities/budgets before reading any WAV.
        for entry in entries:
            single._check(cancel)
            if not isinstance(entry,(str,dict)):raise ValueError('session entry must be a path or object')
            session=load_session(base/entry) if isinstance(entry,str) else validate_session(entry)
            if session.get('coordinate_frame_id')!=bundle['coordinate_frame_id']:raise ValueError('coordinate_frame_mismatch')
            if session['session_id'] in session_ids:raise ValueError('duplicate source session_id')
            session_ids.add(session['session_id']);sessions.append(session)
            total_records+=len(session['captures'])
            if total_records>MAX_RECORDS:raise ValueError('joint capture resource limit exceeded')
        _receiver_calibration(bundle,[dict(session=session) for session in sessions],cancel)
        for a,session in enumerate(sessions):
            single._check(cancel);observations=[]
            for capture in session['captures']:
                single._check(cancel)
                digest=None;input_evidence=None
                try:
                    samples,rate,digest,input_evidence=read_recording_evidence_snapshot(capture['recording_path'])
                    if capture.get('sha256') and capture['sha256']!=digest:raise ValueError('recording checksum differs')
                    acquisition=input_evidence.get('acquisition')
                    if acquisition is not None and not acquisition['processing_eligible']:
                        observation=dict(capture_id=capture['capture_id'],status='rejected',candidates=[],
                            diagnostics=[dict(code='acquisition_not_continuous',message=', '.join(acquisition['rejection_reasons']))])
                    else:
                        observation=process_recording(samples,rate,session['probe'],capture['capture_id'],sound_speed_m_s=session.get('sound_speed_m_s',343),cancel=cancel)
                except (OSError,ValueError,KeyError) as exc:
                    observation=dict(capture_id=capture['capture_id'],status='rejected',candidates=[],diagnostics=[dict(code='recording_rejected',message=str(exc))])
                observation.update({key:capture[key] for key in ('receiver_position_m','receiver_position_std_m','receiver_pose_group_id','provenance') if key in capture})
                observation['input_diagnostics']=list(capture.get('diagnostics',[]))
                observation['input_format']=capture.get('format','unspecified_lossless')
                observation['session_id']=session['session_id']
                if input_evidence is not None:
                    observation['waveform_sha256']=input_evidence['waveform_sha256']
                    observation['input_format']=input_evidence['format']
                    observation['input_diagnostics']=list(dict.fromkeys(observation['input_diagnostics']+input_evidence['diagnostics']))
                    if input_evidence.get('acquisition') is not None:observation['acquisition_evidence']=input_evidence['acquisition']
                if digest is not None:observation['recording_sha256']=digest
                observations.append(observation)
            processed.append(dict(session=session,observations=observations))
            if progress:progress(.2*(a+1)/len(entries),'Processed source session')
        reject_reused_waveforms([observation for item in processed for observation in item['observations']])
        result=infer_scene_bundle(processed,bundle,method=method,cancel=cancel,progress=progress)
        result['runtime_s']=time.perf_counter()-start
        result['provenance']=dict(physical_validation=False,geometry='inferred from recording-derived excess delays',evidence_classes=sorted({o.get('provenance','unspecified') for item in processed for o in item['observations']}),effective_speed_semantics='metres per source-buffer second')
        fingerprint=json.dumps(dict(bundle=bundle,recordings=[[o.get('recording_sha256') for o in item['observations']] for item in processed],method=method),sort_keys=True,allow_nan=False)
        result['result_id']='scene-'+hashlib.sha256(fingerprint.encode()).hexdigest()[:20]
        return result
    except single._Cancelled:out['status']='cancelled'
    except (ValueError,KeyError,TypeError,OSError) as exc:out['diagnostics'].append(str(exc))
    out['processed_sessions']=processed;out['runtime_s']=time.perf_counter()-start
    return out
