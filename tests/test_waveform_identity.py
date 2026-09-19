"""Exact content copies cannot become independent evidence by repackaging."""
import copy,hashlib,io,json,struct,tempfile,unittest,zipfile
from pathlib import Path
import numpy as np
from scipy.io import wavfile
from echosight.storage import waveform_sha256,read_recording_evidence_snapshot,SessionStore,read_recording,load_session
from echosight.pipeline import process_session
from echosight.simulation import simulate_session
from tests.test_acquisition import capture_bytes

class WaveformIdentityTests(unittest.TestCase):
    def test_canonical_content_identity_preserves_original_values(self):
        x=np.array([0.,-0.,2**-35,.25]);before=x.tobytes()
        y=x.copy();y[:2]=0
        self.assertEqual(waveform_sha256(x,48000),waveform_sha256(y,48000));self.assertEqual(x.tobytes(),before)
        for other,rate in [(x,44100),(x[:-1],48000),(x+1e-10,48000)]:
            self.assertNotEqual(waveform_sha256(x,48000),waveform_sha256(other,rate))
        # Chunking must preserve the byte-level canonical definition.
        big=np.tile(x,40000)
        expected=hashlib.sha256(b'echosight-mono-float64-waveform-v1\0'+(48000).to_bytes(4,'little')+len(big).to_bytes(8,'little'))
        canonical=big.astype('<f8');canonical[canonical==0]=0.;expected.update(canonical.tobytes())
        self.assertEqual(waveform_sha256(big,48000),expected.hexdigest())

    def test_five_lossless_containers_share_content_but_keep_distinct_raw_hashes(self):
        x=np.array([0.,-.25,.125,.5],np.float64);a=io.BytesIO();wavfile.write(a,48000,(x*32768).astype(np.int16));pcm=a.getvalue()
        extra=b'JUNK'+struct.pack('<I',4)+b'test';padded=pcm[:4]+struct.pack('<I',len(pcm)+len(extra)-8)+pcm[8:]+extra
        native,floating,_=capture_bytes(x)
        stream=io.BytesIO()
        with zipfile.ZipFile(stream,'w') as z:z.writestr('audio.csv','sample_value,reported_rate_Hz\n'+''.join(f'{v:.17g},48000\n' for v in x))
        with tempfile.TemporaryDirectory() as tmp:
            raw_hashes=[];waveform_hashes=[]
            for i,raw in enumerate((pcm,padded,floating,native,stream.getvalue())):
                path=Path(tmp)/f'input-{i}';path.write_bytes(raw)
                decoded,rate,digest,evidence=read_recording_evidence_snapshot(path)
                np.testing.assert_array_equal(decoded,x);self.assertEqual(path.read_bytes(),raw)
                raw_hashes.append(digest);waveform_hashes.append(evidence['waveform_sha256'])
            self.assertEqual(len(set(raw_hashes)),5);self.assertEqual(len(set(waveform_hashes)),1)

    def test_every_copied_pose_rejected_through_import_and_replay(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);s=load_session(simulate_session(root/'room',seed=1701,capture_count=12))
            source=Path(s['captures'][0]['recording_path']);samples,_=read_recording(source)
            raw,_,_=capture_bytes(samples);native=root/'copy.zip';native.write_bytes(raw)
            with SessionStore(root/'store') as store:
                sid=store.create_session({k:v for k,v in s.items() if k not in ('session_id','captures')})['session_id']
                for i,c in enumerate(s['captures']):
                    metadata={k:v for k,v in c.items() if k in ('capture_id','receiver_position_m','receiver_position_std_m','provenance')}
                    store.add_recording(sid,source if i%2 else native,metadata)
                result=process_session(store.get_session(sid));archive=store.export_session(sid,root/'archive.zip')
            with SessionStore(root/'reload') as store:
                imported=store.import_archive(archive);replayed=process_session(store.get_session(imported['session_id']))
            for output in (result,replayed):
                self.assertFalse(output['surfaces']);self.assertEqual(len(output['observations']),12)
                self.assertTrue(all(o['status']=='rejected' and not o['candidates'] for o in output['observations']))
                self.assertTrue(all('recording_waveform_reused' in str(o['diagnostics']) for o in output['observations']))
                self.assertEqual(len({o['waveform_sha256'] for o in output['observations']}),1)
                self.assertEqual(len({o['recording_sha256'] for o in output['observations']}),2)

    def test_controlled_epochs_cannot_repackage_identical_audio_as_new_repeats(self):
        from evaluation.controlled_development import recording_protocol
        from echosight.controlled import process_controlled_protocol
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=recording_protocol(root/'raw','moved',receiver_count=4)
            for target,source in ((2,1),(3,0)):
                for i,c in enumerate(p['epochs'][target]['session']['captures']):
                    samples,_=read_recording(p['epochs'][source]['session']['captures'][i]['recording_path'])
                    path=root/f'repackage-{target}-{i}.wav';wavfile.write(path,48000,samples.astype(np.float32));c['recording_path']=str(path)
            result=process_controlled_protocol(p)
            self.assertEqual(result['status'],'inconclusive');self.assertFalse(result['receiver_evidence'])
            self.assertIn('recording_waveforms_reused',str(result['diagnostics']))

if __name__=='__main__':unittest.main()
