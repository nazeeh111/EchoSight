"""Bounded measured-route admission and small numerical/display checks."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import struct
import tempfile
import subprocess
import unittest
from unittest.mock import patch
import zlib
import numpy as np
from scipy.interpolate import interpn
from echosight import nlos


class NLOSAdmission(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.source=self.root/'input.mat';self.source.write_bytes(b'test')
        self.output=self.root/'result'
    def tearDown(self):self.temp.cleanup()
    def call(self,**kw):
        return nlos.process_fig2(self.source,self.output,preset=nlos.PRESET,
            sample_rate_hz=1000000,memory_budget_gib=6,**kw)
    def test_wrong_size_hash_and_symlink_before_decoder_or_output(self):
        with patch('scipy.io.loadmat') as decoder:
            with self.assertRaises(ValueError):self.call()
            with patch.object(nlos,'INPUT_BYTES',4):
                with self.assertRaises(ValueError):self.call()
            self.source.unlink();target=self.root/'owned';target.write_bytes(b'test');self.source.symlink_to(target)
            with self.assertRaises(ValueError):self.call()
            decoder.assert_not_called()
        self.assertFalse(self.output.exists())
    def test_unsupported_rate_preset_budget_before_any_output(self):
        for preset,rate,budget in [('other',1000000,6),(nlos.PRESET,48000,6),(nlos.PRESET,1000000,1),(nlos.PRESET,1000000,float('nan'))]:
            with self.subTest(preset=preset,rate=rate,budget=budget),self.assertRaises(ValueError):
                nlos.process_fig2(self.source,self.output,preset=preset,sample_rate_hz=rate,memory_budget_gib=budget)
        self.assertFalse(self.output.exists())
    def test_existing_output_never_changed(self):
        self.output.mkdir();marker=self.output/'owned';marker.write_bytes(b'owned')
        with self.assertRaises(ValueError):self.call()
        self.assertEqual(marker.read_bytes(),b'owned')
    def test_estimate_only_verifies_pinned_bytes_without_decode_or_output(self):
        with patch.object(nlos,'INPUT_BYTES',4),patch.object(nlos,'INPUT_SHA256',hashlib.sha256(b'test').hexdigest()),patch('scipy.io.loadmat') as decoder:
            result=self.call(estimate_only=True)
            self.assertEqual(result['status'],'verified_input_estimate_only')
            self.assertEqual(result['expected_input']['shape'],[55,55,25000])
            decoder.assert_not_called()
        self.assertFalse(self.output.exists())
    def test_snapshot_survives_original_path_replacement(self):
        with patch.object(nlos,'INPUT_BYTES',4),patch.object(nlos,'INPUT_SHA256',hashlib.sha256(b'test').hexdigest()):
            with nlos.verified_snapshot(self.source) as snapshot:
                self.source.rename(self.root/'original');self.source.write_bytes(b'evil')
                self.assertEqual(snapshot.read(),b'test')
    def test_timeout_retains_failure_and_reaps_only_created_worker(self):
        class Worker:
            pid=123;stopped=False
            def poll(self):return 0 if self.stopped else None
            def kill(self):self.stopped=True
            def wait(self,timeout=None):
                if not self.stopped:raise subprocess.TimeoutExpired('owned test worker',300)
                return -9
        worker=Worker()
        with patch.object(nlos,'INPUT_BYTES',4),patch.object(nlos,'INPUT_SHA256',hashlib.sha256(b'test').hexdigest()),patch('echosight.nlos.subprocess.Popen',return_value=worker),contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(subprocess.TimeoutExpired):self.call()
        self.assertTrue(worker.stopped)
        self.assertEqual(json.loads((self.output/'FAILED.json').read_text())['status'],'failed_or_inconclusive')
        self.assertFalse((self.output/'report.json').exists())
    def test_cli_timeout_is_concise_nonzero_without_traceback(self):
        from echosight.cli import main
        stream=io.StringIO()
        with patch('echosight.nlos.process_fig2',side_effect=subprocess.TimeoutExpired('owned test worker',300)),contextlib.redirect_stderr(stream):
            code=main(['nlos-fig2','--input',str(self.source),'--output',str(self.output),'--preset',nlos.PRESET,'--sample-rate-hz','1000000'])
        self.assertEqual(code,2);self.assertIn('wall deadline',stream.getvalue());self.assertNotIn('Traceback',stream.getvalue())


class NLOSArithmetic(unittest.TestCase):
    def test_stolt_matches_independent_dense_interpolation(self):
        rng=np.random.default_rng(918);n,m=3,7;a=.17
        values=rng.normal(size=(2*m,2*n,2*n))+1j*rng.normal(size=(2*m,2*n,2*n))
        za=np.arange(-m,m)/m;xy=np.arange(-n,n)/n
        z,y,x=np.meshgrid(za,xy,xy,indexing='ij');q=np.sqrt(abs(a*a*(x*x+y*y)+z*z))
        expected=interpn((za,xy,xy),values,np.stack([q,y,x],axis=-1),bounds_error=False,fill_value=0)
        expected*=z>0;expected*=abs(z)/np.maximum(q,1e-6)
        self.assertLess(np.max(abs(expected-nlos.stolt_slabs(values,n,m,a,slab=2))),2e-13)
    def test_png_is_real_lossless_rgb_and_unknown_depth_is_black(self):
        from echosight.nlos_display import png_bytes,display_arrays
        depth=np.array([[np.nan,1.2],[1.4,1.5]]);amp=np.array([[0.,.2],[.5,1.]])
        color,gray=display_arrays(depth,amp)
        # Display reverses both axes; unknown is bottom right, not zero depth.
        self.assertEqual(color[-1,-1].tolist(),[0,0,0])
        raw=png_bytes(color);self.assertEqual(raw[:8],b'\x89PNG\r\n\x1a\n')
        pos=8;chunks={}
        while pos<len(raw):
            size=struct.unpack_from('>I',raw,pos)[0];tag=raw[pos+4:pos+8];data=raw[pos+8:pos+8+size]
            self.assertEqual(zlib.crc32(tag+data)&0xffffffff,struct.unpack_from('>I',raw,pos+8+size)[0])
            chunks[tag]=data;pos+=12+size
        self.assertEqual(zlib.decompress(chunks[b'IDAT']),b''.join(b'\0'+row.tobytes() for row in color))
    def test_axial_display_bytes_bind_native_source_bins_without_resampling(self):
        from echosight.nlos_display import axial_display,substitute
        volume=np.arange(20*3*3,dtype=float).reshape(20,3,3)
        raw,spec=axial_display(volume,.1)
        expected=np.flip(np.rint(volume[9:17]/volume.max()*255).astype(np.uint8),axis=(1,2))
        self.assertEqual(raw,expected.tobytes())
        self.assertEqual(spec['first_volume_index_zero_based'],9)
        self.assertEqual(spec['sha256'],hashlib.sha256(raw).hexdigest())
        self.assertEqual(substitute('A B',{'A':'B','B':'unchanged'}),'B unchanged')

if __name__=='__main__':unittest.main()
