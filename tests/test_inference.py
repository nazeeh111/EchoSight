import unittest
import numpy as np
from echosight.inference import infer_scene, infer_baseline, recommend_next_view
from echosight.geometry import image_source, excess_delay, reflection_point


def fixture(coplanar=False, clutter=False):
    source = np.array([2., 2., 1.1])
    receivers = np.array([[.7,.8,.5],[3.4,.7,1.8],[.9,3.4,1.4],[3.6,3.,.6],
                          [1.4,1.2,2.1],[2.8,3.5,1.9],[.5,2.3,1.0],[3.2,1.8,.9]])
    planes=[([1,0,0],0),([1,0,0],4.7),([0,1,0],0),([0,1,0],4.3),([0,0,1],0),([0,0,1],2.9)]
    if coplanar:
        receivers[:,2]=source[2]
        planes=[([0,0,1],2.9)]
    session=dict(session_id='test',source_position_m=source.tolist(),source_position_std_m=.001,
                 sound_speed_m_s=343.,sound_speed_std_m_s=.1,source_clock_scale=1.,source_clock_std_ppm=10)
    observations=[]
    for i,r in enumerate(receivers):
        candidates=[dict(candidate_id=f'{i}-{j}',delay_s=float(excess_delay(source,r,image_source(source,n,d),343)),delay_std_s=1e-5,amplitude=1.) for j,(n,d) in enumerate(planes)]
        if clutter: candidates += [dict(candidate_id=f'{i}-clutter',delay_s=.0013+i*.0009,delay_std_s=1e-5,amplitude=.7)]
        observations.append(dict(capture_id=str(i),status='ok',receiver_position_m=r.tolist(),receiver_position_std_m=.001,direct_std_s=1e-5,candidates=candidates))
    return session,observations,planes


class InferenceTests(unittest.TestCase):
    def test_bistatic_forward_and_point(self):
        s=np.array([2.,2.,1.2]);r=np.array([3.,3.,1.2]);q=image_source(s,[1,0,0],5)
        self.assertAlmostEqual(excess_delay(s,r,q,343),(np.sqrt(26)-np.sqrt(2))/343)
        p=reflection_point(s,r,[1,0,0],5)
        self.assertAlmostEqual(p[0],5)
    def test_room_unlabeled(self):
        s,o,planes=fixture(clutter=True);out=infer_scene(s,o)
        self.assertEqual(len(out['surfaces']),6,out)
        for n,d in planes:
            self.assertTrue(any(abs(abs(np.dot(n,p['normal']))-1)<1e-3 and abs(abs(p['offset_m'])-abs(d))<.015 for p in out['surfaces']))
        used=[(e['capture_id'],e['candidate_id']) for p in out['surfaces'] for e in p['support']]
        self.assertEqual(len(used),len(set(used)))
        self.assertTrue(all(p['extent_status']=='unknown' for p in out['surfaces']))
    def test_mirror_ambiguity(self):
        s,o,_=fixture(coplanar=True);out=infer_scene(s,o)
        self.assertEqual(out['status'],'ambiguous',out)
        self.assertGreaterEqual(len(out['hypotheses']),2)
        self.assertIn('height',str(out['guidance']))
    def test_null_cancel_and_insufficient(self):
        s,o,_=fixture()
        self.assertEqual(infer_scene(s,o,cancel=lambda: True)['status'],'cancelled')
        self.assertEqual(infer_scene(s,o[:3])['status'],'no_result')
        for x in o: x['candidates']=[]
        self.assertEqual(infer_scene(s,o)['status'],'no_result')
    def test_uncertainty_shared_and_residual(self):
        s,o,_=fixture();a=infer_scene(s,o)
        s['source_position_std_m']=.1;b=infer_scene(s,o)
        self.assertGreater(np.mean([p['uncertainty']['offset_std_m'] for p in b['surfaces']]),np.mean([p['uncertainty']['offset_std_m'] for p in a['surfaces']]))
        self.assertLess(max(abs(e['residual_s']) for p in a['surfaces'] for e in p['support']),1e-7)
    def test_baseline_same_shape(self):
        s,o,_=fixture();out=infer_baseline(s,o)
        self.assertIn('surfaces',out)
        self.assertEqual(out['method'],'direct_plane_grid_baseline')

    def test_candidate_clutter_no_definitive_surfaces(self):
        for seed in range(10):
            s,o,_=fixture();rng=np.random.default_rng(seed)
            for row in o:
                row['candidates']=[dict(candidate_id=f"{row['capture_id']}-{j}",delay_s=float(t),delay_std_s=4e-5,amplitude=1.) for j,t in enumerate(rng.uniform(.001,.04,6))]
            out=infer_scene(s,o)
            self.assertEqual(out['surfaces'],[],(seed,out))

    def test_off_receiver_plane_source_still_mirrored(self):
        s,o,_=fixture(coplanar=True);s['source_position_m'][2]+=.3
        source=np.array(s['source_position_m']);q=image_source(source,[0,0,1],2.9)
        for row in o:row['candidates'][0]['delay_s']=float(excess_delay(source,row['receiver_position_m'],q,343))
        out=infer_scene(s,o)
        self.assertEqual(out['status'],'ambiguous');self.assertEqual(out['surfaces'],[])
        self.assertEqual(out['hypotheses'][1]['hypothesis_id'],'coplanar_mirror')

    def test_unmatched_elevated_view_does_not_remove_mirror(self):
        s,o,_=fixture(coplanar=True)
        o.append(dict(capture_id='extra',status='ok',receiver_position_m=[1.,1.3,2.],receiver_position_std_m=.001,direct_std_s=1e-5,
                      candidates=[dict(candidate_id='unrelated',delay_s=.06,delay_std_s=1e-5,amplitude=1.)]))
        out=infer_scene(s,o)
        self.assertEqual(out['status'],'ambiguous');self.assertEqual(out['surfaces'],[])

    def test_repeated_poses_do_not_confirm_geometry(self):
        s,o,_=fixture();o=o[:4]+[dict(x,capture_id='repeat'+x['capture_id']) for x in o[:4]]
        out=infer_scene(s,o)
        self.assertEqual(out['surfaces'],[])
        self.assertIn('repeated_receiver_position_not_independent_view',out['diagnostics'])

    def test_active_view_separates_mirror(self):
        s,o,_=fixture(coplanar=True);out=infer_scene(s,o);source=np.array(s['source_position_m'])
        same=(source+np.array([.4,.5,0.])).tolist();elevated=(source+np.array([.4,.5,.8])).tolist()
        guidance=recommend_next_view(s,out,[same,elevated])
        self.assertEqual(guidance['suggested_position_m'],elevated)
        self.assertGreater(guidance['score_sigma'],10)
        self.assertLess(guidance['candidates'][1]['score_sigma'],1e-8)
