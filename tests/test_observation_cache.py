"""Observation reuse never substitutes admission, inference, or interpretation."""
import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from echosight.observation_cache import ObservationCache
from echosight.pipeline import process_session
from echosight.simulation import simulate_session
from echosight.storage import load_session
from echosight.signals import process_recording
from echosight.inference import infer_scene


def scientific(result):
    result = copy.deepcopy(result)
    result.pop('runtime_s', None)
    result['provenance'].pop('observation_cache', None)
    return result


class ObservationCacheTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.session = load_session(simulate_session(self.temp.name, seed=2, capture_count=5))
        self.session['captures'] = self.session['captures'][:4]
        self.cache = ObservationCache()

    def test_exact_warm_reuse_and_pose_refits(self):
        cold = process_session(self.session)
        with patch('echosight.signals.process_recording', wraps=process_recording) as dsp, patch('echosight.inference.infer_scene', wraps=infer_scene) as inference:
            first = process_session(self.session, observation_cache=self.cache)
            warm = process_session(self.session, observation_cache=self.cache)
            self.assertEqual(dsp.call_count, 4); self.assertEqual(inference.call_count, 2)
        self.assertEqual(scientific(cold), scientific(first)); self.assertEqual(scientific(cold), scientific(warm))
        self.assertEqual(warm['provenance']['observation_cache']['hit'],4)
        moved=copy.deepcopy(self.session); moved['captures'][0]['receiver_position_m'][0] += .05
        with patch('echosight.signals.process_recording', wraps=process_recording) as dsp, patch('echosight.inference.infer_scene', wraps=infer_scene) as inference:
            cached=process_session(moved, observation_cache=self.cache)
            self.assertEqual(dsp.call_count,0);self.assertEqual(inference.call_count,1)
        self.assertEqual(scientific(cached),scientific(process_session(moved)))
        self.assertNotEqual(cached['result_id'],warm['result_id'])

    def test_added_capture_and_changed_inputs_miss(self):
        process_session(self.session,observation_cache=self.cache)
        expanded=load_session(Path(self.temp.name)/'session.json')
        with patch('echosight.signals.process_recording', wraps=process_recording) as dsp:
            result=process_session(expanded,observation_cache=self.cache)
            self.assertEqual(dsp.call_count,1);self.assertEqual(result['provenance']['observation_cache']['hit'],4)
        changed=copy.deepcopy(self.session); changed['sound_speed_m_s']=349.0
        with patch('echosight.signals.process_recording', wraps=process_recording) as dsp:
            process_session(changed,observation_cache=self.cache);self.assertEqual(dsp.call_count,4)
        changed=copy.deepcopy(self.session);changed['probe']['low_hz'] += 10
        with patch('echosight.signals.process_recording', wraps=process_recording) as dsp:
            process_session(changed,observation_cache=self.cache);self.assertEqual(dsp.call_count,4)
        with patch('echosight.pipeline.platform.python_version',return_value='different-runtime'), patch('echosight.signals.process_recording',wraps=process_recording) as dsp:
            process_session(self.session,observation_cache=self.cache);self.assertEqual(dsp.call_count,4)

    def test_bad_source_and_duplicate_waveforms_never_bypass_admission(self):
        process_session(self.session,observation_cache=self.cache)
        changed=copy.deepcopy(self.session);changed['captures'][0]['sha256']='0'*64
        result=process_session(changed,observation_cache=self.cache)
        self.assertEqual(result['observations'][0]['status'],'rejected');self.assertIn('checksum',str(result['observations'][0]))
        dup=copy.deepcopy(self.session);dup['captures'][1]['recording_path']=dup['captures'][0]['recording_path'];dup['captures'][1].pop('sha256',None)
        result=process_session(dup,observation_cache=self.cache)
        self.assertTrue(all(x['status']=='rejected' for x in result['observations'][:2]))
        self.assertIn('recording_waveform_reused',str(result['observations']))

    def test_eviction_corruption_and_no_cross_run_mutation(self):
        c=ObservationCache(max_entries=1,max_bytes=1000,max_entry_bytes=1000)
        self.assertTrue(c.put('a',{'status':'ok','nested':[1]}));value,_=c.get('a');value['nested'][0]=9;self.assertEqual(c.get('a')[0]['nested'],[1])
        self.assertTrue(c.put('b',{'status':'ok'}));self.assertEqual(c.get('a')[1],'miss')
        c._entries['b']=(b'{bad', 'wrong');self.assertEqual(c.get('b')[1],'corrupt')
        self.assertFalse(c.put('huge',{'status':'ok','x':'x'*1001}))
        self.assertEqual(ObservationCache().get('b')[1],'miss')

    def test_changed_waveform_and_source_revision_recompute(self):
        import numpy as np
        from scipy.io import wavfile
        process_session(self.session, observation_cache=self.cache)
        changed=copy.deepcopy(self.session)
        capture=changed['captures'][0]; path=Path(capture['recording_path'])
        rate, values=wavfile.read(path);values=values.copy();values[0] = values[0] + 1
        wavfile.write(path, rate, values);capture.pop('sha256',None)
        with patch('echosight.signals.process_recording',wraps=process_recording) as dsp:
            result=process_session(changed,observation_cache=self.cache)
            self.assertEqual(dsp.call_count,1);self.assertEqual(result['provenance']['observation_cache']['hit'],3)
        read=Path.read_bytes
        def modified_source(path):
            raw=read(path)
            return raw+b'\n# simulated implementation revision' if path.name=='signals.py' else raw
        with patch.object(Path,'read_bytes',modified_source), patch('echosight.signals.process_recording',wraps=process_recording) as dsp:
            process_session(changed,observation_cache=self.cache);self.assertEqual(dsp.call_count,4)

    def test_native_ineligibility_and_declarations_rechecked(self):
        from tests.test_acquisition import capture_bytes
        from echosight.storage import read_recording
        session=copy.deepcopy(self.session)
        for i,capture in enumerate(session['captures']):
            samples,_=read_recording(capture['recording_path'])
            def native(m): m['source_declaration'].update(configuration_id='same',probe_id='same',route_id='same')
            raw,_,_=capture_bytes(samples,native);path=Path(self.temp.name)/f'native-{i}.zip';path.write_bytes(raw)
            capture['recording_path']=str(path);capture.pop('sha256',None)
        process_session(session,observation_cache=self.cache)
        with patch('echosight.signals.process_recording',wraps=process_recording) as dsp:
            warm=process_session(session,observation_cache=self.cache);self.assertEqual(dsp.call_count,0)
        self.assertEqual(warm['source_declaration_consistency']['status'],'consistent_declarations')
        samples,_=read_recording(session['captures'][0]['recording_path'])
        def interrupted(m):
            m['events'].append({'type':'interruption','at_frame':10,'detail':'test'})
        raw,_,_=capture_bytes(samples,interrupted);Path(session['captures'][0]['recording_path']).write_bytes(raw)
        result=process_session(session,observation_cache=self.cache)
        self.assertEqual(result['observations'][0]['status'],'rejected')
        self.assertIn('acquisition_not_continuous',str(result['observations'][0]))
        samples,_=read_recording(session['captures'][1]['recording_path'])
        def conflict(m): m['source_declaration'].update(configuration_id='other',probe_id='same',route_id='same')
        raw,_,_=capture_bytes(samples,conflict);Path(session['captures'][1]['recording_path']).write_bytes(raw)
        result=process_session(session,observation_cache=self.cache)
        self.assertEqual(result['source_declaration_consistency']['status'],'contradictory')
        self.assertEqual(result['status'],'no_result')

    def test_corrupted_entry_recomputes_before_admission(self):
        first=process_session(self.session,observation_cache=self.cache)
        key=next(iter(self.cache._entries));data,checksum=self.cache._entries[key]
        self.cache._entries[key]=(data+b' ',checksum)
        with patch('echosight.signals.process_recording',wraps=process_recording) as dsp:
            second=process_session(self.session,observation_cache=self.cache)
        self.assertEqual(dsp.call_count,1);self.assertEqual(second['provenance']['observation_cache']['corrupt'],1)
        self.assertEqual(scientific(first),scientific(second))

    def test_mutation_after_snapshot_never_changes_cached_input_identity(self):
        import echosight.storage as storage
        capture=self.session['captures'][0]; path=Path(capture['recording_path']); original=path.read_bytes()
        baseline=process_session(self.session,observation_cache=self.cache)
        decode=storage._decode_recording_evidence; once=[False]
        def mutate_after_capture(raw):
            decoded=decode(raw)
            if not once[0]:
                once[0]=True;changed=bytearray(original);changed[-1]^=1;path.write_bytes(changed)
            return decoded
        with patch.object(storage,'_decode_recording_evidence',side_effect=mutate_after_capture):
            result=process_session(self.session,observation_cache=self.cache)
        self.assertEqual(result['observations'][0],baseline['observations'][0])
        self.assertEqual(result['provenance']['observation_cache']['hit'],4)
        later=process_session(self.session,observation_cache=self.cache)
        self.assertNotEqual(later['observations'][0].get('recording_sha256'),baseline['observations'][0]['recording_sha256'])
        self.assertLess(later['provenance']['observation_cache']['hit'],4)

    def test_nominal_rate_change_is_cache_miss(self):
        from scipy.io import wavfile
        process_session(self.session,observation_cache=self.cache)
        changed=copy.deepcopy(self.session);capture=changed['captures'][0];path=Path(capture['recording_path'])
        rate,values=wavfile.read(path);wavfile.write(path,rate-1000,values);capture.pop('sha256',None)
        with patch('echosight.signals.process_recording',wraps=process_recording) as dsp:
            result=process_session(changed,observation_cache=self.cache)
        self.assertEqual(dsp.call_count,1);self.assertEqual(result['provenance']['observation_cache']['hit'],3)

    def test_concurrent_cache_calls_are_bounded(self):
        from concurrent.futures import ThreadPoolExecutor
        c=ObservationCache(max_entries=3,max_bytes=1000,max_entry_bytes=1000)
        def task(i):
            for j in range(100):
                key=str((i+j)%7);c.put(key,{'status':'ok','key':key});value,status=c.get(key)
                if status=='hit':self.assertEqual(value['key'],key)
        with ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(task,range(4)))
        self.assertLessEqual(len(c._entries),3);self.assertLessEqual(c._size,1000)

    def test_cancelled_work_is_not_cached(self):
        def cancel_result(*args,**kwargs):
            return {'capture_id':args[3], 'status':'rejected','diagnostics':[{'code':'cancelled'}],'candidates':[]}
        with patch('echosight.signals.process_recording',side_effect=cancel_result):
            process_session(self.session,observation_cache=self.cache)
        with patch('echosight.signals.process_recording',wraps=process_recording) as dsp:
            process_session(self.session,observation_cache=self.cache);self.assertEqual(dsp.call_count,4)
