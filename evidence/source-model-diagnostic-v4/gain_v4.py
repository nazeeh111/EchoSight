"""Box-constrained two-column least squares by interior and all four edges."""
import numpy as np

def bounded_gains(a,b,y):
    y=np.asarray(y,dtype=float);a=np.broadcast_to(np.asarray(a,dtype=float),y.shape);b=np.broadcast_to(np.asarray(b,dtype=float),y.shape)
    A=np.sum(a*a,axis=-1);B=np.sum(b*b,axis=-1);C=np.sum(a*b,axis=-1);u=np.sum(a*y,axis=-1);v=np.sum(b*y,axis=-1)
    safeA=np.where(A>0,A,1.);safeB=np.where(B>0,B,1.)
    # Feasible single-column candidates give zero secondary gain when its column vanishes.
    pairs=[(np.clip(u/safeA,0.,2.),np.zeros_like(B)),(np.zeros_like(A),np.clip(v/safeB,-2.,2.))]
    for ga in (0.,2.):pairs.append((np.full_like(A,ga),np.clip((v-C*ga)/safeB,-2.,2.)))
    for gb in (-2.,2.):pairs.append((np.clip((u-C*gb)/safeA,0.,2.),np.full_like(B,gb)))
    determinant=A*B-C*C;regular=determinant>64*np.finfo(float).eps*A*B
    denominator=np.where(regular,determinant,1.)
    ga=(u*B-v*C)/denominator;gb=(v*A-u*C)/denominator
    feasible=regular&(ga>=0)&(ga<=2)&(gb>=-2)&(gb<=2)
    pairs.append((np.where(feasible,ga,0.),np.where(feasible,gb,0.)))
    coefficients=np.stack([np.stack(p,axis=-1) for p in pairs],axis=0)
    residual=y[None,...]-coefficients[...,0,None]*a[None,...]-coefficients[...,1,None]*b[None,...]
    costs=np.sum(residual*residual,axis=-1);costs[-1]=np.where(feasible,costs[-1],np.inf)
    choice=np.argmin(costs,axis=0);indices=np.arange(len(y))
    return coefficients[choice,indices],residual[choice,indices]
