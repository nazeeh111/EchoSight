"""Physical feature ratios and rejection boundaries; no semantic material priors."""
import copy
import hashlib
import unittest
import numpy as np
from scipy.signal import fftconvolve
from echosight.signals import generate_probe, process_recording
from echosight.geometry import image_source, reflection_point


class MaterialFeatureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source=np.array([1.5,1.5,1.3]);receiver=np.array([.7,2.4,1.9]);normal=np.array([1.,0.,0.]);offset=0.
        q=image_source(source,normal,offset);direct=np.linalg.norm(receiver-source);length=np.linalg.norm(receiver-q)
        waveform,probe=generate_probe(dict(high_hz=14000.));fs=probe['sample_rate_hz']
        # Fractional propagation uses a bandlimited delay; linear interpolation
        # would itself color direct/echo differently and falsify this ratio test.
        impulse=np.zeros(round(.1*fs))
        for distance,amplitude in ((direct,.55),(length,.55*.4*direct/length)):
            center=distance/343.*fs;indices=np.arange(int(np.floor(center))-24,int(np.floor(center))+25)
            weights=np.sinc(indices-center)*np.hanning(49);weights/=weights.sum()
            impulse[indices]+=amplitude*weights
        samples=np.r_[np.zeros(round(.08*fs)),fftconvolve(waveform,impulse),np.zeros(round(.05*fs))]
        samples+=np.random.default_rng(319).normal(0,.00001,len(samples))
        samples=np.rint(samples*32767).astype('<i2').astype(float)/32768
        observation=process_recording(samples,fs,probe,'capture-0')
        assert observation['status']=='ok' and len(observation['candidates'])==1
        observation.update(receiver_position_m=receiver.tolist(),receiver_position_std_m=.003,
            recording_sha256=hashlib.sha256(samples.tobytes()).hexdigest(),waveform_sha256=hashlib.sha256(b'waveform'+samples.tobytes()).hexdigest())
        candidate=observation['candidates'][0]
        surface=dict(surface_id='reflector-test',kind='unclassified_planar_reflector',model_status='conditional_first_order_hypothesis',
            normal=normal.tolist(),offset_m=offset,image_source_m=q.tolist(),support=[dict(capture_id='capture-0',candidate_id=candidate['candidate_id'],
            observed_delay_s=candidate['delay_s'],predicted_delay_s=(length-direct)/343.,reflection_point_m=reflection_point(source,receiver,normal,offset).tolist())])
        cls.result=dict(result_id='result-features-test',session_id='material-test',status='partial',surfaces=[surface],observations=[observation],
            acquisition=dict(session_id='material-test',coordinate_frame_id='test-frame',source_position_m=source.tolist(),sound_speed_m_s=343.,source_clock_scale=1.,probe=probe,
                captures=[dict(capture_id='capture-0',receiver_position_m=receiver.tolist(),receiver_position_std_m=.003)]))

    def extract(self,result=None,cancel=None):
        from echosight.material_features import extract_surface_features
        r=result if result is not None else copy.deepcopy(self.result)
        return extract_surface_features(r,r['surfaces'][0],cancel=cancel)

    def test_recording_derived_reflection_ratio_and_common_gain(self):
        from echosight.material_features import FEATURE_VERSION,BANDS_HZ
        result=copy.deepcopy(self.result);before=copy.deepcopy(result);row=self.extract(result)[0]
        self.assertEqual(row['status'],'ok',row)
        np.testing.assert_allclose(row['feature_db'],20*np.log10(.4),atol=.5)
        self.assertEqual(row['feature_version'],FEATURE_VERSION)
        self.assertEqual(row['bands_hz'],[list(b) for b in BANDS_HZ])
        self.assertEqual(len(row['probe_sha256']),64)
        self.assertEqual(result,before)
        scaled=copy.deepcopy(result);o=scaled['observations'][0]
        o['response']['values']=[x*3 for x in o['response']['values']]
        for key in ('noise_response_amplitude','direct_response_amplitude'):o['quality'][key]*=3
        np.testing.assert_allclose(self.extract(scaled)[0]['feature_db'],row['feature_db'],atol=1e-10)

    def test_known_echo_gain_changes_each_band_without_absorption_claim(self):
        result=copy.deepcopy(self.result);o=result['observations'][0];response=o['response'];delay=o['candidates'][0]['delay_s'];rate=response['sample_rate_hz']
        center=round((delay-response['start_delay_s'])*rate);width=round(.001*rate)
        for i in range(center-width,center+width+1):response['values'][i]*=.5
        baseline=self.extract()[0];changed=self.extract(result)[0]
        self.assertEqual(changed['status'],'ok',changed)
        np.testing.assert_allclose(np.array(changed['feature_db'])-baseline['feature_db'],20*np.log10(.5),atol=1e-10)
        self.assertNotIn('absorption_coefficient',changed)

    def test_overlap_and_missing_hash_keep_rejected_support(self):
        r=copy.deepcopy(self.result);o=r['observations'][0];other=copy.deepcopy(o['candidates'][0]);other.update(candidate_id='neighbour',delay_s=other['delay_s']+.0004);o['candidates'].append(other)
        row=self.extract(r)[0];self.assertEqual(row['status'],'unknown');self.assertIn('overlapping_detected_paths',row['diagnostic_codes']);self.assertNotIn('feature_db',row)
        r=copy.deepcopy(self.result);del r['observations'][0]['waveform_sha256']
        row=self.extract(r)[0];self.assertEqual(row['status'],'unknown');self.assertIn('recording_identity_unavailable',row['diagnostic_codes'])

    def test_forged_support_and_receiver_declarations_reject(self):
        for change in ('candidate','delay','receiver','surface','duplicate_observation'):
            r=copy.deepcopy(self.result)
            if change=='candidate':r['surfaces'][0]['support'][0]['candidate_id']='forged'
            if change=='delay':r['surfaces'][0]['support'][0]['observed_delay_s']+=.0005
            if change=='receiver':r['acquisition']['captures'][0]['receiver_position_m'][0]+=.1
            if change=='surface':r['surfaces'][0]['image_source_m'][1]+=.1
            if change=='duplicate_observation':r['observations'].append(copy.deepcopy(r['observations'][0]))
            with self.subTest(change=change):
                row=self.extract(r)[0];self.assertEqual(row['status'],'unknown');self.assertNotIn('feature_db',row)

    def test_invalid_band_clock_noise_and_response_are_unknown(self):
        for change in ('rate','units','band','nan','truncated','noise','zero','merged','budget'):
            r=copy.deepcopy(self.result);o=r['observations'][0]
            if change=='rate':o['response']['sample_rate_hz']=44100
            if change=='units':o['response']['delay_unit']='physical_seconds'
            if change=='band':o['quality']['usable_band_hz']=[3000.,14000.]
            if change=='nan':o['response']['values'][0]=float('nan')
            if change=='truncated':o['response']['values']=o['response']['values'][:10]
            if change=='noise':o['quality']['noise_response_amplitude']=1.
            if change=='zero':o['response']['values']=[0.]*len(o['response']['values'])
            if change=='merged':o['candidates'][0]['merged']=True
            if change=='budget':o['diagnostics'].append({'code':'candidate_budget'})
            with self.subTest(change=change):
                row=self.extract(r)[0];self.assertEqual(row['status'],'unknown');self.assertNotIn('feature_db',row)

    def test_cancelled_or_unavailable_geometry_never_has_features(self):
        for status in ('cancelled','ambiguous','no_result','calibration_needed'):
            r=copy.deepcopy(self.result);r['status']=status
            self.assertTrue(all(row['status']=='unknown' for row in self.extract(r)))
        self.assertIn('cancelled',self.extract(cancel=lambda:True)[0]['diagnostic_codes'])
        calls=0
        def cancel():
            nonlocal calls
            calls+=1
            return calls>1
        self.assertTrue(all(row['status']=='unknown' for row in self.extract(cancel=cancel)))

    def test_long_window_contamination_returns_unknown(self):
        result=copy.deepcopy(self.result);o=result['observations'][0];response=o['response'];rate=response['sample_rate_hz']
        center=round((o['candidates'][0]['delay_s']-response['start_delay_s'])*rate)
        # A strong unlisted transient is outside the short window but inside the diagnostic window.
        response['values'][center+round(.0006*rate)]+=5.
        row=self.extract(result)[0]
        self.assertEqual(row['status'],'unknown')
        self.assertIn('window_sensitive_spectrum',row['diagnostic_codes'])

    def test_completed_ok_geometry_is_also_eligible(self):
        result=copy.deepcopy(self.result);result['status']='ok'
        self.assertEqual(self.extract(result)[0]['status'],'ok')

    def test_probe_fingerprint_canonical_and_bound_to_actual_probe(self):
        from echosight.material_features import probe_fingerprint
        probe=self.result['acquisition']['probe'];self.assertEqual(probe_fingerprint(probe),probe_fingerprint(dict(high_hz=14000.)))
        self.assertNotEqual(probe_fingerprint(probe),probe_fingerprint(dict(high_hz=15000.)))
        with self.assertRaises(ValueError):probe_fingerprint(dict(probe,waveform_sha256='0'*64))
        with self.assertRaises(ValueError):probe_fingerprint(dict(probe,sample_rate_hz=float('nan')))

if __name__=='__main__':unittest.main()
