"""Physical bistatic geometry. Metres, seconds, z-up; n·x=d."""
import numpy as np
from scipy.spatial import ConvexHull, QhullError


def image_source(source, normal, offset):
    s, n = np.asarray(source, float), np.asarray(normal, float)
    return s + 2 * (offset - n @ s) * n


def plane_from_image(source, image):
    s, q = np.asarray(source, float), np.asarray(image, float)
    n = q - s
    length = np.linalg.norm(n)
    if length < 1e-8:
        raise ValueError('Image source coincides with source')
    n /= length
    d = float(n @ ((s + q) / 2))
    if n[np.argmax(np.abs(n))] < 0:
        n, d = -n, -d
    return n, d


def excess_delay(source, receiver, image, effective_speed):
    s, r, q = map(lambda x: np.asarray(x, float), (source, receiver, image))
    return (np.linalg.norm(r - q, axis=-1) - np.linalg.norm(r - s, axis=-1)) / effective_speed


def reflection_point(source, receiver, normal, offset):
    s, r, n = map(lambda x: np.asarray(x, float), (source, receiver, normal))
    if (n @ s - offset) * (n @ r - offset) <= 1e-10:
        return None
    q = image_source(s, n, offset)
    denominator = n @ (q-r)
    if abs(denominator) < 1e-10:
        return None
    fraction = (offset-n @ r)/denominator
    if not 0 < fraction < 1:
        return None
    return r + fraction*(q-r)


def support_mesh(points, normal):
    """Convex hull of observed reflection points, never physical surface edges."""
    pts = np.unique(np.asarray(points, float), axis=0)
    if len(pts) < 3:
        return pts.tolist(), []
    n=np.asarray(normal,float);axis=np.eye(3)[np.argmin(np.abs(n))]
    u=np.cross(n,axis);u/=np.linalg.norm(u);v=np.cross(n,u)
    flat=np.column_stack((pts@u,pts@v))
    try:
        ring=pts[ConvexHull(flat).vertices]
    except QhullError:
        return pts.tolist(), []
    return ring.tolist(), [[0,i,i+1] for i in range(1,len(ring)-1)]


def sphere_intersections(centers, radii):
    """Both intersections of three spheres; empty for inconsistent/collinear data."""
    a,b,c=np.asarray(centers,float);ra,rb,rc=np.asarray(radii,float)
    d=np.linalg.norm(b-a)
    if d<1e-8: return []
    ex=(b-a)/d;i=ex@(c-a); ey=c-a-i*ex;j=np.linalg.norm(ey)
    if j<1e-8: return []
    ey/=j;ez=np.cross(ex,ey)
    x=(ra*ra-rb*rb+d*d)/(2*d)
    y=(ra*ra-rc*rc+i*i+j*j-2*i*x)/(2*j)
    z2=ra*ra-x*x-y*y
    if z2 < -1e-8: return []
    base=a+x*ex+y*ey;z=np.sqrt(max(0,z2))
    return [base+z*ez,base-z*ez]


def reflection_path(source, receiver, planes):
    """Unfold and validate a specular path in the supplied reflection order.

    Returns no path when an intersection lies outside its unfolded ray segment
    or the reflected direction is inconsistent. Plane extents and occlusion
    are unknown, so a returned path establishes geometric possibility only.
    """
    s,r=np.asarray(source,float),np.asarray(receiver,float)
    images=[];q=s.copy();normalized=[]
    for normal,offset in planes:
        n=np.asarray(normal,float);length=np.linalg.norm(n)
        if not np.isfinite(length) or length<1e-10:return None
        n=n/length;d=float(offset)/length;normalized.append((n,d))
        q=image_source(q,n,d);images.append(q)
    if not images:return None
    point=r.copy();reverse=[]
    for (n,d),image in reversed(list(zip(normalized,images))):
        denominator=n@(image-point)
        if abs(denominator)<1e-10:return None
        fraction=(d-n@point)/denominator
        if not 1e-8<fraction<1-1e-8:return None
        point=point+fraction*(image-point);reverse.append(point)
    vertices=np.array([s]+list(reversed(reverse))+[r]);segments=np.diff(vertices,axis=0)
    lengths=np.linalg.norm(segments,axis=1)
    if np.any(lengths<1e-8):return None
    directions=segments/lengths[:,None];errors=[]
    for i,(n,d) in enumerate(normalized):
        reflected=directions[i]-2*(directions[i]@n)*n
        errors.append(float(np.linalg.norm(reflected-directions[i+1])))
    error=max(errors)
    if error>1e-6:return None
    return dict(vertices_m=vertices.tolist(),length_m=float(lengths.sum()),
                image_source_m=images[-1].tolist(),max_reflection_law_error=error,
                extent_and_occlusion_status='unknown')
