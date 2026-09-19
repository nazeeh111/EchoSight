"""Exact delivered-sample preservation and independent capture-clock checks."""
import copy
import hashlib
import io
import json
from pathlib import Path
import struct
import tempfile
import unittest
import zipfile
import numpy as np
from scipy.io.wavfile import write


def capture_bytes(samples=None, mutate=None):
    x=np.asarray(samples if samples is not None else [0.,-0.,2**-35,.125,.12345678,-.9876543],dtype='<f4')
    audio=io.BytesIO();write(audio,48000,x);audio=audio.getvalue();n=len(x);half=n//2
    blocks=[{'sequence':i,'first_frame':a,'frame_count':b-a,'sample_time_valid':True,'sample_time':str(a),
        'host_time_valid':True,'host_time':str(1000000000+round(a*1e9/48000))} for i,(a,b) in enumerate([(0,half),(half,n)])]
    m={'schema_version':'1.0','format':'echosight_capture','capture_id':'record-1',
        'recording_sha256':hashlib.sha256(audio).hexdigest(),'sample_encoding':'ieee_float32_le',
        'sample_rate_hz':48000,'channel_count':1,'frame_count':n,
        'recorder':{'name':'EchoSight native','version':'1'},'acquisition_layer':'ios_audioengine_delivered_buffers',
        'device':{'model':'simulated','os_version':'fixture'},
        'source_declaration':{'configuration_id':'unknown','probe_id':'probe-one','route_id':'unknown'},
        'session':{'category':'record','mode':'measurement','preferred_sample_rate_hz':48000,'activated_sample_rate_hz':48000},
        'route_initial':{'input_port_type':'builtInMic','input_port_name':'Microphone','input_channel_count':1,'input_sample_rate_hz':48000},
        'host_timebase':{'numer':1,'denom':1},'continuity':{'status':'complete','reasons':[],'blocks':blocks},
        'events':[{'type':'user_stop','at_frame':n,'detail':'fixture'}]}
    m['route_final']=copy.deepcopy(m['route_initial'])
    if mutate:mutate(m)
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w',compression=zipfile.ZIP_STORED) as z:
        z.writestr('recording.wav',audio);z.writestr('manifest.json',json.dumps(m))
    return stream.getvalue(),audio,x


class AcquisitionTests(unittest.TestCase):
    def test_float_wav_exact_values_and_original_bytes(self):
        from echosight.storage import read_recording,import_recording
        _,audio,x=capture_bytes()
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'input.wav';path.write_bytes(audio)
            samples,rate=read_recording(path)
            self.assertEqual(rate,48000)
            self.assertEqual(samples.astype('<f4').tobytes(),x.tobytes())
            imported=import_recording(path,Path(tmp)/'raw')
            self.assertEqual(Path(imported['recording_path']).read_bytes(),audio)
            self.assertEqual(imported['format'],'ieee_float32_wav')

    def test_capture_manifest_and_float_samples_share_one_verified_snapshot(self):
        from echosight.storage import read_recording_evidence_snapshot,import_recording
        raw,audio,x=capture_bytes()
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'capture.zip';path.write_bytes(raw)
            samples,rate,digest,evidence=read_recording_evidence_snapshot(path)
            self.assertEqual(samples.astype('<f4').tobytes(),x.tobytes())
            self.assertEqual(digest,hashlib.sha256(raw).hexdigest())
            self.assertTrue(evidence['acquisition']['processing_eligible'])
            self.assertFalse(evidence['acquisition']['physical_validation'])
            imported=import_recording(path,Path(tmp)/'raw')
            self.assertEqual(Path(imported['recording_path']).read_bytes(),raw)
            self.assertEqual(imported['format'],'echosight_capture_zip')
            self.assertEqual(imported['acquisition']['recording_sha256'],hashlib.sha256(audio).hexdigest())

    def test_reported_complete_does_not_hide_gap_or_changed_route(self):
        from echosight.storage import read_recording_evidence_snapshot
        for mutation in [lambda m:m['continuity']['blocks'][1].update(sample_time='4'),
                         lambda m:m['route_final'].update(input_port_type='Bluetooth'),
                         lambda m:m['continuity']['blocks'][1].update(host_time='1'),
                         lambda m:m['events'].append({'type':'interruption','at_frame':3,'detail':'test'})]:
            raw,_,_=capture_bytes(mutate=mutation)
            with tempfile.TemporaryDirectory() as tmp:
                path=Path(tmp)/'capture.zip';path.write_bytes(raw)
                _,_,_,evidence=read_recording_evidence_snapshot(path)
                self.assertFalse(evidence['acquisition']['processing_eligible'])
                self.assertTrue(evidence['acquisition']['rejection_reasons'])

    def test_host_and_sample_clocks_must_describe_consistent_intervals(self):
        from echosight.storage import read_recording_evidence_snapshot
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'capture.zip'
            for ticks in ('2000000000','1000000001'):
                raw,_,_=capture_bytes(mutate=lambda m:m['continuity']['blocks'][1].update(host_time=ticks))
                path.write_bytes(raw);e=read_recording_evidence_snapshot(path)[3]['acquisition']
                self.assertFalse(e['processing_eligible'])
                self.assertIn('host_sample_time_inconsistent',e['rejection_reasons'])
            raw,_,_=capture_bytes(mutate=lambda m:m['host_timebase'].update(numer=2**32-1))
            path.write_bytes(raw);e=read_recording_evidence_snapshot(path)[3]['acquisition']
            self.assertFalse(e['processing_eligible'])
            self.assertIn('host_timer_resolution_unqualified',e['rejection_reasons'])
            raw,_,_=capture_bytes(np.zeros(48000),mutate=lambda m:m['continuity']['blocks'][1].update(host_time='1502500000'))
            path.write_bytes(raw);e=read_recording_evidence_snapshot(path)[3]['acquisition']
            self.assertTrue(e['processing_eligible'])  # +5000ppm stays inside stated engineering gate

    def test_native_package_enters_raw_mapping_and_interruption_cannot_be_overridden(self):
        from echosight.simulation import simulate_session
        from echosight.storage import load_session,read_recording
        from echosight.pipeline import process_session
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);session=load_session(simulate_session(root/'room',seed=1,capture_count=12))
            for i,capture in enumerate(session['captures']):
                samples,_=read_recording(capture['recording_path'])
                raw,_,_=capture_bytes(samples)
                path=root/f'capture-{i}.zip';path.write_bytes(raw);capture['recording_path']=str(path)
            result=process_session(session)
            self.assertEqual(len(result['surfaces']),6)
            self.assertTrue(all(o['acquisition_evidence']['processing_eligible'] for o in result['observations']))
            self.assertFalse(result['provenance']['physical_validation'])
            samples,_=read_recording(session['captures'][0]['recording_path'])
            raw,_,_=capture_bytes(samples,lambda m:m['events'].append({'type':'interruption','at_frame':10,'detail':'test'}))
            Path(session['captures'][0]['recording_path']).write_bytes(raw)
            session['captures'][0]['acquisition']={'processing_eligible':True}
            result=process_session(session);first=result['observations'][0]
            self.assertEqual(first['status'],'rejected')
            self.assertEqual(first['candidates'],[])
            self.assertFalse(first['acquisition_evidence']['processing_eligible'])
            self.assertIn('recording_sha256',first)

    def test_import_export_reload_preserves_package_and_rechecks_acquisition(self):
        from echosight.storage import SessionStore
        raw,_,_=capture_bytes(mutate=lambda m:m['continuity'].update(status='interrupted',reasons=['test']))
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);path=root/'input.zip';path.write_bytes(raw)
            with SessionStore(root/'store') as store:
                sid=store.create_session({})['session_id']
                capture=store.add_recording(sid,path,{'capture_id':'c','provenance':'simulated'})
                self.assertFalse(capture['acquisition']['processing_eligible'])
                archive=store.export_session(sid,root/'export.zip')
            with SessionStore(root/'reload') as store:
                session=store.import_archive(archive);capture=session['captures'][0]
                actual=store.get_session(session['session_id'])['captures'][0]
                self.assertEqual(Path(actual['recording_path']).read_bytes(),raw)
                self.assertFalse(capture['acquisition']['processing_eligible'])

    def test_package_resource_and_member_integrity_limits(self):
        from echosight.acquisition import read_capture_package
        raw,audio,_=capture_bytes()
        with self.assertRaises(ValueError):read_capture_package(raw,128)
        variants=[{'manifest.json':b'{}','recording.wav':audio,'../extra':b'x'},
                  {'manifest.json':b'['*10000,'recording.wav':audio},
                  {'manifest.json':b'x'*(1024*1024+1),'recording.wav':audio},
                  {'manifest.json':b'\xff','recording.wav':audio}]
        for members in variants:
            stream=io.BytesIO()
            with zipfile.ZipFile(stream,'w') as archive:
                for name,data in members.items():archive.writestr(name,data)
            with self.assertRaises(ValueError):read_capture_package(stream.getvalue(),64*1024*1024)
        # CRC mismatch is a malformed package, not unverified-but-processable audio.
        broken=bytearray(raw);offset=raw.index(b'RIFF');broken[offset+20]^=1
        for malformed in (bytes(broken),raw[:-20]):
            with self.assertRaises(ValueError):read_capture_package(malformed,64*1024*1024)
        oversized,_,_=capture_bytes(mutate=lambda m:m['continuity'].update(blocks=[m['continuity']['blocks'][0]]*16385))
        with self.assertRaises(ValueError):read_capture_package(oversized,64*1024*1024)

    def test_structural_integrity_nonfinite_and_resource_failures(self):
        from echosight.storage import read_recording
        for mutation in [lambda m:m.update(recording_sha256='0'*64),lambda m:m.update(frame_count=9),
                         lambda m:m['continuity']['blocks'][1].update(first_frame=4),
                         lambda m:m['host_timebase'].update(denom=0),
                         lambda m:(m['continuity']['blocks'][0].update(sample_time_valid=False),m['continuity']['blocks'][0].pop('sample_time'))]:
            raw,_,_=capture_bytes(mutate=mutation)
            with tempfile.TemporaryDirectory() as tmp:
                path=Path(tmp)/'capture.zip';path.write_bytes(raw)
                with self.assertRaises(ValueError):read_recording(path)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'bad.wav'
            for x in [np.array([0,np.nan],np.float32),np.array([0,np.inf],np.float32)]:
                write(path,48000,x)
                with self.assertRaises(ValueError):read_recording(path)
            stream=io.BytesIO();write(stream,48000,np.zeros(8,np.float32));raw=stream.getvalue()
            path.write_bytes(raw[:-1])
            with self.assertRaises(ValueError):read_recording(path)

class AcquisitionHTTPTests(unittest.TestCase):
    def test_original_package_upload_to_geometry_and_export(self):
        import threading,time,urllib.request,urllib.error
        from echosight.api import create_server
        from echosight.simulation import simulate_session
        from echosight.storage import load_session,read_recording
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);session=load_session(simulate_session(root/'room',seed=1,capture_count=12))
            server=create_server(root/'store',port=0)
            worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
            url='http://127.0.0.1:'+str(server.server_address[1])
            def request(method,path,data=None,headers=None):
                if isinstance(data,dict):data=json.dumps(data).encode()
                req=urllib.request.Request(url+path,data=data,method=method,headers=headers or {})
                try:
                    with urllib.request.urlopen(req) as response:return response.status,response.read()
                except urllib.error.HTTPError as exc:return exc.code,exc.read()
            try:
                metadata={k:v for k,v in session.items() if k not in ('captures','session_id')}
                code,body=request('POST','/v1/sessions',metadata);self.assertEqual(code,201,body)
                route='/v1/sessions/'+json.loads(body)['session_id'];originals=[]
                for capture in session['captures']:
                    samples,_=read_recording(capture['recording_path']);raw,_,_=capture_bytes(samples);originals.append(raw)
                    metadata={k:v for k,v in capture.items() if k in ('capture_id','receiver_position_m','receiver_position_std_m','provenance','device_id','receiver_pose_group_id','notes')}
                    code,body=request('POST',route+'/recordings',raw,{'X-Capture-Metadata':json.dumps(metadata)})
                    self.assertEqual(code,201,body)
                malformed,_,_=capture_bytes(mutate=lambda m:m.update(recording_sha256='0'*64))
                code,_=request('POST',route+'/recordings',malformed);self.assertEqual(code,400)
                _,body=request('GET',route);self.assertEqual(len(json.loads(body)['captures']),12)
                code,body=request('POST',route+'/jobs',{});self.assertEqual(code,202,body);jid=json.loads(body)['job_id']
                for _ in range(300):
                    _,body=request('GET','/v1/jobs/'+jid);job=json.loads(body)
                    if job['status'] in ('completed','failed'):break
                    time.sleep(.02)
                self.assertEqual(job['status'],'completed',job)
                code,body=request('GET',route+'/result');self.assertEqual(code,200,body);result=json.loads(body)
                self.assertEqual(len(result['surfaces']),6)
                self.assertFalse(result['provenance']['physical_validation'])
                self.assertTrue(all(o['acquisition_evidence']['processing_eligible'] for o in result['observations']))
                code,archive=request('GET',route+'/export');self.assertEqual(code,200)
                with zipfile.ZipFile(io.BytesIO(archive)) as z:
                    payloads=[z.read(n) for n in z.namelist() if n.startswith('raw/')]
                self.assertTrue(all(raw in payloads for raw in originals))
            finally:server.shutdown();server.server_close();worker.join()

if __name__=='__main__':unittest.main()
