import io
import struct
import unittest
import zlib
import numpy as np
from scipy.io import savemat
from evaluation.stress_simulation import lattice_images,fractional_rir,reflected
from evaluation.flair_subset import matrix_header

class AuditHarnessChecks(unittest.TestCase):
    def test_image_lattice_counts_and_first_order_distances(self):
        source=np.array([1.,1.5,1.2]);size=np.array([5.,4.,3.])
        self.assertEqual(len(lattice_images(source,size,1)),7)
        self.assertEqual(len(lattice_images(source,size,2)),25)
        actual=[q for q,k in lattice_images(source,size,1) if k==1]
        for axis in range(3):
            for bound in [0.,size[axis]]:
                q=source.copy();q[axis]=2*bound-q[axis]
                self.assertTrue(any(np.allclose(q,p) for p in actual))

    def test_fractional_impulse_area_and_delay(self):
        coordinate=435.37
        h=fractional_rir([(coordinate/48000,.8,'path')],48000)
        self.assertAlmostEqual(h.sum(),.8,places=12)
        self.assertLess(abs(np.sum(h*np.arange(len(h)))/h.sum()-coordinate),.001)

    def test_finite_reflection_true_bistatic_path(self):
        s=np.array([1.,2.,1.]);r=np.array([2.,1.,1.5]);n=np.array([1.,0.,0.]);d=4.
        q,p=reflected(s,r,n,d)
        self.assertAlmostEqual(p@n,d)
        self.assertAlmostEqual(np.linalg.norm(s-p)+np.linalg.norm(p-r),np.linalg.norm(q-r))
        self.assertIsNone(reflected(s,np.array([5.,2.,1.]),n,d))

    def test_partial_matlab_column_major_extraction(self):
        arr=np.arange(5*4*2,dtype=float).reshape(5,4,2)
        f=io.BytesIO();savemat(f,{'rirs':arr},do_compression=True);data=f.getvalue()
        kind,size=struct.unpack('<II',data[128:136]);self.assertEqual(kind,15)
        decoded=zlib.decompress(data[136:136+size]);name,shape,start,count=matrix_header(decoded)
        self.assertEqual((name,shape),('rirs',(5,4,2)))
        recovered=np.frombuffer(decoded[start:start+count],dtype='<f8').reshape(shape,order='F')
        np.testing.assert_array_equal(recovered,arr)

if __name__=='__main__':unittest.main()
