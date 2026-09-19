"""Bounded competing interpretations on fixed multi-source echo assignments.

Engineering residual gates are not probabilities. An alternative withholds a
specific plane; it never establishes absent walls or a physical object's shape.
"""
import hashlib
import numpy as np
from scipy.linalg import solve_triangular
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from .geometry import reflection_path
from .inference import _check

MAX_STARTS = 32
MAX_RECORDS = 64
MAX_SURFACES = 10
MAX_PARENT_ANGLES = 180

def _evidence(surface,processed,speed,calcov):
    session_index={p['session']['session_id']:i for i,p in enumerate(processed)}
    lookup={(p['session']['session_id'],o['capture_id']):(p['session'],o) for p in processed for o in p['observations']}
    rows=[];keys=[]
    for link in surface['support']:
        sid=link['session_id'];cid=link['capture_id'];key=(sid,cid)
        if key in keys:raise ValueError('one candidate per recording required')
        keys.append(key);session,observation=lookup[key]
        peak=next((p for p in observation['candidates'] if p['candidate_id']==link['candidate_id']),None)
        if peak is None:raise ValueError('selected candidate is missing')
        capture=next((c for c in session.get('captures',[]) if c['capture_id']==cid),{})
        group=observation.get('receiver_pose_group_id',capture.get('receiver_pose_group_id'))
        if not group:raise ValueError('selected receiver survey group is missing')
        rows.append({'source_index':session_index[sid],'source':np.asarray(session['source_position_m']),
            'receiver':np.asarray(observation['receiver_position_m']),'peak':peak,'observation':observation,
            'key':(sid,cid,peak['candidate_id']),'group':group})
    s=np.array([r['source'] for r in rows]);r=np.array([row['receiver'] for row in rows]);y=np.array([row['peak']['delay_s'] for row in rows]);n=np.array(surface['normal']);d=surface['offset_m']
    q=s+2*(d-s@n)[:,None]*n;direct=np.linalg.norm(s-r,axis=1);distance=np.linalg.norm(q-r,axis=1);mu=(distance-direct)/speed
    u=(q-r)/distance[:,None];u0=(s-r)/direct[:,None];source_gradient=(u@(np.eye(3)-2*np.outer(n,n))-u0)/speed;receiver_gradient=(u0-u)/speed
    A=np.zeros((len(rows),len(calcov)));C=np.zeros((len(rows),len(rows)))
    for i,row in enumerate(rows):
        a=row['source_index'];A[i,3*a:3*a+3]=source_gradient[i];A[i,-1]=-mu[i]/speed
        observation=row['observation'];clock=observation.get('clock',{})
        C[i,i]=max(float(row['peak'].get('delay_std_s',1e-5)),1e-7)**2+observation.get('direct_std_s',1e-5)**2+mu[i]**2*(clock.get('alpha_std',0)/clock.get('alpha',1))**2
    C+=A@calcov@A.T
    for i,left in enumerate(rows):
        for j,right in enumerate(rows):
            if left['group']==right['group']:
                C[i,j]+=receiver_gradient[i]@receiver_gradient[j]*left['observation'].get('receiver_position_std_m',.01)**2
    return rows,s,r,y,speed,C,mu,q


def prediction(p,s,r,v):
    return (np.linalg.norm(s-p,axis=1)+np.linalg.norm(r-p,axis=1)-np.linalg.norm(s-r,axis=1))/v

def derivatives(p,s,r,v):
    a=(s-p)/np.maximum(np.linalg.norm(s-p,axis=1)[:,None],1e-12)
    b=(r-p)/np.maximum(np.linalg.norm(r-p,axis=1)[:,None],1e-12)
    u=(s-r)/np.maximum(np.linalg.norm(s-r,axis=1)[:,None],1e-12)
    return -(a+b)/v,(a-u)/v,(b+u)/v

def fit_point(s,r,y,v,C,cancel=None):
    origin=np.mean(s,axis=0);chol=np.linalg.cholesky(C)
    def residual(x):
        _check(cancel)
        return solve_triangular(chol,prediction(origin+x,s,r,v)-y,lower=True)
    def jac(x):return solve_triangular(chol,derivatives(origin+x,s,r,v)[0],lower=True)
    starts=[np.zeros(3),np.clip(np.mean(r,axis=0)-origin,-14,14)]
    for k in range(30):
        z=1-2*(k+.5)/30;phi=k*np.pi*(3-np.sqrt(5));direction=np.array([np.sqrt(1-z*z)*np.cos(phi),np.sqrt(1-z*z)*np.sin(phi),z])
        starts.append(direction*[1.,4.,10.][k%3])
    fits=[least_squares(residual,start,jac=jac,bounds=(-15,15),max_nfev=100,ftol=1e-10,xtol=1e-10,gtol=1e-10) for start in starts]
    best=min(fits,key=lambda f:f.fun@f.fun);q=float(best.fun@best.fun);p=origin+best.x
    minima=[]
    for fit in sorted(fits,key=lambda f:f.fun@f.fun):
        position=origin+fit.x
        if any(np.linalg.norm(position-np.array(a['position_m']))<.01 for a in minima):continue
        minima.append({'position_m':position.tolist(),'Q':float(fit.fun@fit.fun),'converged':bool(fit.success),'nfev':fit.nfev,'search_boundary_limited':bool(np.any(abs(fit.x)>14.999))})
    singular=np.linalg.svd(best.jac,compute_uv=False);rank=int(np.count_nonzero(singular>singular[0]*1e-8))
    pcov=np.linalg.pinv(best.jac.T@best.jac,rcond=1e-16);boundary=bool(np.any(abs(best.x)>14.999))
    error=y-prediction(p,s,r,v)
    return {'position_m':p.tolist(),'Q':q,'rms_s':float(np.sqrt(np.mean(error**2))),'max_error_s':float(np.max(abs(error))),
        'max_marginal_standardized_residual':float(np.max(abs(error)/np.sqrt(np.diag(C)))),
        'rank':rank,'jacobian_singular_values':singular.tolist(),'conditional_position_covariance_m2':pcov.tolist() if rank==3 and not boundary else None,
        'conditional_position_std_m':np.sqrt(np.diag(pcov)).tolist() if rank==3 and not boundary else None,'search_boundary_limited':boundary,'minima':minima[:MAX_STARTS],
        'equal_quality_separated_minima':sum(a['Q']<=q+1e-6*(1+q) for a in minima),'optimizer_success':bool(best.success),
        'covariance_semantics':'Fixed-objective curvature diagnostic only; exported location modes separately propagate actual compact-path nuisance covariance.'}

def fit_plane(surface,s,r,y,v,C,cancel=None):
    n=np.array(surface['normal']);d=surface['offset_m'];e=np.eye(3)[np.argmin(abs(n))];u=np.cross(n,e);u/=np.linalg.norm(u);w=np.cross(n,u)
    origin=s.mean(axis=0);locald=d-n@origin;L=np.linalg.cholesky(C)
    def model(x):
        _check(cancel)
        a=n+x[0]*u+x[1]*w;a/=np.linalg.norm(a);offset=locald+x[2]+a@origin
        q=s+2*(offset-s@a)[:,None]*a
        return (np.linalg.norm(q-r,axis=1)-np.linalg.norm(s-r,axis=1))/v
    fit=least_squares(lambda x:solve_triangular(L,model(x)-y,lower=True),np.zeros(3),max_nfev=100)
    original=solve_triangular(L,model(np.zeros(3))-y,lower=True)
    return {'original_Q':float(original@original),'refit_Q':float(fit.fun@fit.fun),'comparison_Q':float(min(original@original,fit.fun@fit.fun)),'refit_parameters':fit.x.tolist()}


def _parent_operator(s,r,y,speed,C,first_images,source_indices,cancel):
    """Five coordinates: rotation vector plus axis-perpendicular center (2).

    Translation along the axis is removed, not assigned a finite uncertainty.
    """
    virtual=[];sources=[]
    for index in sorted(set(source_indices)):
        _check(cancel)
        mask=source_indices==index;centers=r[mask];ranges=np.linalg.norm(s[mask]-centers,axis=1)+speed*y[mask]
        A=2*(centers[1:]-centers[0]);b=np.sum(centers[1:]**2,axis=1)-centers[0]@centers[0]-(ranges[1:]**2-ranges[0]**2)
        linear=np.linalg.lstsq(A,b,rcond=None)[0]
        def residual(q):
            _check(cancel)
            return np.linalg.norm(q-centers,axis=1)-ranges
        fits=[least_squares(residual,start,max_nfev=64) for start in [linear,first_images[mask][0]]]
        fit=min(fits,key=lambda f:f.fun@f.fun);virtual.append(fit.x);sources.append(s[mask][0])
    sources=np.array(sources);virtual=np.array(virtual);origin=sources.mean(axis=0)
    U,_,Vt=np.linalg.svd((sources-origin).T@(virtual-virtual.mean(axis=0)))
    R=Vt.T@np.diag([1,1,np.linalg.det(Vt.T@U.T)])@U.T
    center=np.linalg.pinv(np.eye(3)-R)@(virtual.mean(axis=0)-R@origin)-origin
    rv=Rotation.from_matrix(R).as_rotvec()
    if np.linalg.norm(rv)<1e-5:return None
    axis=rv/np.linalg.norm(rv);anchor=np.eye(3)[np.argmin(abs(axis))]
    def frame(vector):
        axis=vector/max(np.linalg.norm(vector),1e-12);u=np.cross(axis,anchor)
        if np.linalg.norm(u)<1e-8:return None
        u/=np.linalg.norm(u);return u,np.cross(axis,u)
    u,w=frame(rv);coordinates=np.array([center@u,center@w]);chol=np.linalg.cholesky(C);direct=np.linalg.norm(s-r,axis=1)
    def transform(params):
        basis=frame(params[:3])
        if basis is None:return None
        u,w=basis;c=origin+params[3]*u+params[4]*w;rot=Rotation.from_rotvec(params[:3]).as_matrix()
        return rot,c
    def residual(params):
        _check(cancel);value=transform(params)
        if value is None:return np.full(len(y),1e6)
        rot,c=value;images=(s-c)@rot.T+c;mu=(np.linalg.norm(images-r,axis=1)-direct)/speed
        return solve_triangular(chol,y-mu,lower=True)
    fits=[]
    for multiplier in [1.,.85,1.15]:
        start=np.r_[np.clip(rv*multiplier,-np.pi+.001,np.pi-.001),np.clip(coordinates,-19.9,19.9)]
        fits.append(least_squares(residual,start,bounds=(np.r_[[-np.pi]*3,[-20.]*2],np.r_[[np.pi]*3,[20.]*2]),max_nfev=100))
    best=min(fits,key=lambda f:f.fun@f.fun);value=transform(best.x)
    if value is None:return None
    singular=np.linalg.svd(best.jac,compute_uv=False);rank=int(np.count_nonzero(singular>singular[0]*1e-7))
    rot,center=value
    return rot,center,dict(parameter_count=5,local_rank=rank,rotation_angle_deg=float(np.degrees(np.linalg.norm(Rotation.from_matrix(rot).as_rotvec()))),operator_Q=float(best.fun@best.fun),gauge='Axis-center translation along the rotation axis eliminated; parent decomposition remains a family.',optimizer_success=bool(best.success))


def _physical_parents(R,center,s,r,y,speed,C,cancel):
    vector=Rotation.from_matrix(R).as_rotvec();theta=np.linalg.norm(vector)
    if theta<1e-5:return None
    axis=vector/theta;basis=np.eye(3)[np.argmin(abs(axis))];u=np.cross(axis,basis);u/=np.linalg.norm(u);w=np.cross(axis,u)
    half=Rotation.from_rotvec(axis*theta/2).as_matrix();direct=np.linalg.norm(s-r,axis=1);chol=np.linalg.cholesky(C);best=None
    for phi in np.linspace(0,np.pi,MAX_PARENT_ANGLES,endpoint=False):
        _check(cancel);n1=np.cos(phi)*u+np.sin(phi)*w;n2=half@n1;planes=[(n1,float(n1@center)),(n2,float(n2@center))]
        prediction=[];orders=[];paths=[]
        for source,receiver,target,base in zip(s,r,y,direct):
            _check(cancel);alternatives=[]
            for order in [(0,1),(1,0)]:
                path=reflection_path(source,receiver,[planes[k] for k in order])
                if path is None:continue
                delay=(path['length_m']-base)/speed
                if delay>0:alternatives.append((abs(target-delay),delay,order,path))
            if not alternatives:break
            _,delay,order,path=min(alternatives,key=lambda item:item[0]);prediction.append(delay);orders.append(order);paths.append(path)
        if len(paths)!=len(y):continue
        error=y-np.array(prediction);white=solve_triangular(chol,error,lower=True);Q=float(white@white)
        if best is None or Q<best['Q']:
            best=dict(Q=Q,planes=[dict(normal=n.tolist(),offset_m=d) for n,d in planes],
                rms_s=float(np.sqrt(np.mean(error**2))),max_error_s=float(np.max(abs(error))),
                max_marginal_standardized_residual=float(np.max(abs(error)/np.sqrt(np.diag(C)))),
                orders=[list(order) for order in orders],path_vertices_m=[path['vertices_m'] for path in paths],predicted_delay_s=prediction,
                extent_and_occlusion_status='unknown',parents_status='One physically valid member of an unobserved parent family; not recovered walls.')
    return best


def _admissible(score,plane_Q):
    return score['Q']<=plane_Q+1e-8*(1+plane_Q) and score['rms_s']<=100e-6 and score['max_error_s']<=200e-6 and score['max_marginal_standardized_residual']<=3


def _point_nuisance_covariance(p,rows,s,r,v,calibration_covariance):
    """Actual compact-path nuisance propagation, separately from score weights."""
    mu=prediction(p,s,r,v);_,source_gradient,receiver_gradient=derivatives(p,s,r,v)
    A=np.zeros((len(rows),len(calibration_covariance)));C=np.zeros((len(rows),len(rows)))
    for i,row in enumerate(rows):
        a=row['source_index'];A[i,3*a:3*a+3]=source_gradient[i];A[i,-1]=-mu[i]/v
        observation=row['observation'];clock=observation.get('clock',{})
        C[i,i]=max(float(row['peak'].get('delay_std_s',1e-5)),1e-7)**2+observation.get('direct_std_s',1e-5)**2
        C[i,i]+=mu[i]**2*(clock.get('alpha_std',0)/clock.get('alpha',1))**2
    # Keep the full matrix, including source/source and source/speed cross terms.
    C+=A@calibration_covariance@A.T
    for i,left in enumerate(rows):
        for j,right in enumerate(rows):
            if left['group']==right['group']:
                C[i,j]+=receiver_gradient[i]@receiver_gradient[j]*left['observation'].get('receiver_position_std_m',.01)**2
    return C


def _fixed_weight_covariance(J,fixed_covariance,actual_covariance):
    """Sandwich for the executed fixed-weight estimator, not an unexecuted GLS.

    L=(J.T W J)^-1 J.T W; covariance=L C_actual L.T, W=C_fixed^-1.
    """
    chol=np.linalg.cholesky(fixed_covariance)
    whitening=solve_triangular(chol,np.eye(len(J)),lower=True)
    influence=np.linalg.pinv(whitening@J,rcond=1e-8)@whitening
    covariance=influence@actual_covariance@influence.T
    return (covariance+covariance.T)/2


def _point_modes(point,s,r,y,v,C,plane_Q,rows,calibration_covariance):
    modes=[];L=np.linalg.cholesky(C)
    for candidate in point['minima']:
        if not candidate['converged']:continue
        p=np.array(candidate['position_m']);error=y-prediction(p,s,r,v);z=solve_triangular(L,error,lower=True)
        score=dict(Q=float(z@z),rms_s=float(np.sqrt(np.mean(error**2))),max_error_s=float(np.max(abs(error))),max_marginal_standardized_residual=float(np.max(abs(error)/np.sqrt(np.diag(C)))))
        if not _admissible(score,plane_Q):continue
        raw_J=derivatives(p,s,r,v)[0];J=solve_triangular(L,raw_J,lower=True);singular=np.linalg.svd(J,compute_uv=False);rank=int(np.count_nonzero(singular>singular[0]*1e-8))
        actual_C=_point_nuisance_covariance(p,rows,s,r,v,calibration_covariance)
        cov=_fixed_weight_covariance(raw_J,C,actual_C)
        modes.append(dict(position_m=p.tolist(),local_rank=rank,conditional_covariance_m2=cov.tolist() if rank==3 and not candidate['search_boundary_limited'] else None,search_boundary_limited=candidate['search_boundary_limited'],covariance_semantics='Mode-specific local sandwich propagation of actual compact-path source/speed/receiver/timing covariance through the executed fixed-weight estimator; conditional on selected paths and the compact scattering model.',score=score))
    return modes


def apply_path_alternatives(out,processed,speed,calibration_covariance,cancel=None):
    """Post-fit interpretation only. Existing ambiguity and hypotheses survive."""
    _check(cancel)
    surfaces=list(out['surfaces'])
    if not surfaces:return
    if len(surfaces)>MAX_SURFACES:raise ValueError('path alternative surface budget exceeded')
    challenged=[];hypotheses=[];comparisons=[]
    for surface in surfaces:
        _check(cancel)
        if not 1<=len(surface['support'])<=MAX_RECORDS:raise ValueError('path alternative record budget exceeded')
        rows,s,r,y,v,C,mu,images=_evidence(surface,processed,speed,calibration_covariance)
        counts=[len({tuple(row['receiver']) for row in rows if row['source_index']==k}) for k in range(len(processed))]
        if min(counts)<4:continue
        plane=fit_plane(surface,s,r,y,v,C,cancel);plane_Q=plane['comparison_Q'];point=fit_point(s,r,y,v,C,cancel)
        modes=_point_modes(point,s,r,y,v,C,plane_Q,rows,calibration_covariance);keys=[list(row['key']) for row in rows]
        identity=hashlib.sha256(surface['surface_id'].encode()).hexdigest()[:16];alternatives=[]
        if modes:
            alternatives.append(dict(hypothesis_id='compact-location-'+identity,kind='compact_scattering_location',surfaces=[],challenged_surface_id=surface['surface_id'],selected_candidate_keys=keys,location_status='unique_conditional_mode' if len(modes)==1 and modes[0]['local_rank']==3 and not modes[0]['search_boundary_limited'] else 'ambiguous',location_modes=modes,reason='The same selected delays fit a compact scattering-location model at least as well as a refitted plane. Material phase, size, directivity and object identity are not established.'))
        parent=_parent_operator(s,r,y,v,C,images,np.array([row['source_index'] for row in rows]),cancel)
        physical=None
        if parent is not None:
            R,center,operator=parent;physical=_physical_parents(R,center,s,r,y,v,C,cancel)
            if physical is not None and operator['optimizer_success'] and _admissible(physical,plane_Q):
                alternatives.append(dict(hypothesis_id='unobserved-parents-'+identity,kind='unobserved_two_reflection_family',surfaces=[],challenged_surface_id=surface['surface_id'],selected_candidate_keys=keys,operator=operator,physical_example=physical,reason='A fixed pair of unobserved parent planes physically explains every selected arrival at least as well. These parents are hypotheses, not recovered structural surfaces.'))
        comparisons.append(dict(surface_id=surface['surface_id'],selected_records=len(rows),source_receiver_counts=counts,plane=plane,point_Q=point['Q'],physical_parent_Q=physical['Q'] if physical is not None else None,alternative_ids=[a['hypothesis_id'] for a in alternatives]))
        if alternatives:challenged.append(surface);hypotheses.extend(alternatives)
    _check(cancel)
    # Apply atomically after every search: cancellation never leaves half a map.
    if challenged:
        ids={s['surface_id'] for s in challenged}
        out['hypotheses'].append(dict(hypothesis_id='challenged_first_order_path_interpretations',surfaces=challenged,reason='Retained original planar interpretations compete with other models on identical selected candidate evidence.'))
        out['hypotheses'].extend(hypotheses);out['surfaces']=[s for s in surfaces if s['surface_id'] not in ids]
        out['status']='partial' if out['surfaces'] else 'ambiguous'
        out['diagnostics'].append('competing_compact_or_unobserved_parent_paths')
    out['path_model_comparison']=dict(comparisons=comparisons,score_semantics='Full fixed-covariance squared residual, not calibrated probability or model odds.',selection_semantics='Exactly the original selected candidate IDs; one arrival per recording per challenged interpretation; hypotheses are alternatives, not simultaneous geometry.',parameter_counts=dict(plane=3,compact_point=3,two_parent_operator=5),limits=dict(surface_count=MAX_SURFACES,records_per_surface=MAX_RECORDS,point_starts=MAX_STARTS,parent_angles=MAX_PARENT_ANGLES),global_optimality_proven=False)
