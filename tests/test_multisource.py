"""Independent analytic source-relocation fixtures; labels never enter inference."""
import copy
import unittest
import numpy as np
from echosight.geometry import image_source,excess_delay
from echosight.multisource import infer_scene_bundle,_calibration


def fixture(hidden=False,degenerate=False,receivers=8):
    rng=np.random.default_rng(7729)
    poses=rng.uniform([.6,.6,.3],[3.8,3.4,2.8],(receivers,3))
    offsets=np.array([[0,0,0],[.7,0,0],[0,.6,0],[.1,.2,.6]])
    if degenerate:offsets=np.array([[0,0,0],[0,0,.2],[0,0,.4],[0,0,.6]])
    sources=np.array([1.2,1.1,.9])+offsets
    planes=[([1,0,0],0),([1,0,0],4.5),([0,1,0],0),([0,1,0],4.2),([0,0,1],0),([0,0,1],3.2)]
    if hidden:planes=[([0,0,1],3.2)]
    processed=[]
    for a,s in enumerate(sources):
        obs=[]
        for i,r in enumerate(poses):
            images=[image_source(s,n,d) for n,d in planes]
            if hidden:images.append(np.array([-s[0],-s[1],s[2]]))
            candidates=[dict(candidate_id=f'{i}-{j}',delay_s=float(excess_delay(s,r,q,343)),delay_std_s=2e-5,amplitude=1.) for j,q in enumerate(images)]
            obs.append(dict(capture_id=str(i),status='ok',receiver_position_m=r.tolist(),receiver_position_std_m=.002,receiver_pose_group_id=f'r{i}',direct_std_s=2e-5,candidates=candidates))
        processed.append(dict(session=dict(session_id=f's{a}',coordinate_frame_id='room',source_position_m=s.tolist()),observations=obs))
    cov=np.kron(np.ones((4,4)),np.eye(3)*.003**2)+np.eye(12)*.004**2
    bundle=dict(schema_version='1.0',scene_id='analytic',coordinate_frame_id='room',scene_static=True,shared_calibration=dict(effective_speed_m_s=343.,effective_speed_std_m_s=.3,covariance_assumption='explicit_source_pose_covariance_independent_speed',source_pose_joint_covariance_m2=cov.tolist()))
    return processed,bundle


class MultiSourceTests(unittest.TestCase):
    def test_room_height_and_exclusive_recording_evidence(self):
        data,bundle=fixture();before=copy.deepcopy(data)
        out=infer_scene_bundle(data,bundle)
        self.assertEqual(len(out['surfaces']),6,out['diagnostics'])
        self.assertGreaterEqual(sum(abs(s['normal'][2])>.99 for s in out['surfaces']),2)
        ids=[(e['session_id'],e['capture_id'],e['candidate_id']) for s in out['surfaces'] for e in s['support']]
        self.assertEqual(len(ids),len(set(ids)));self.assertEqual(data,before)
        self.assertTrue(all(s['confidence']['supporting_source_poses']==4 for s in out['surfaces']))
    def test_hidden_parents_source_move_discriminates_alias(self):
        data,bundle=fixture(hidden=True);out=infer_scene_bundle(data,bundle)
        self.assertEqual(len(out['surfaces']),1,out)
        self.assertGreater(abs(out['surfaces'][0]['normal'][2]),.99)
    def test_tangent_sources_remain_ambiguous(self):
        data,bundle=fixture(hidden=True,degenerate=True);out=infer_scene_bundle(data,bundle)
        self.assertEqual(out['surfaces'],[]);self.assertEqual(out['status'],'ambiguous')
        self.assertTrue(out['hypotheses'])
    def test_missing_shared_calibration_and_frame_rejected(self):
        data,bundle=fixture();bad=copy.deepcopy(bundle);bad['shared_calibration'].pop('covariance_assumption')
        self.assertEqual(infer_scene_bundle(data,bad)['status'],'calibration_needed')
        data[1]['session']['coordinate_frame_id']='other'
        self.assertEqual(infer_scene_bundle(data,bundle)['surfaces'],[])
        self.assertIn('coordinate_frame_mismatch',infer_scene_bundle(data,bundle)['diagnostics'])
    def test_shared_calibration_not_divided_by_source_count(self):
        data,bundle=fixture();v,cov=_calibration(bundle,4)
        self.assertAlmostEqual(cov[-1,-1],.3**2)
        self.assertAlmostEqual(cov[0,3],.003**2)
        low=infer_scene_bundle(data,bundle)
        bundle['shared_calibration']['effective_speed_std_m_s']=3.
        high=infer_scene_bundle(data,bundle)
        self.assertGreater(np.trace(high['shared_plane_parameter_covariance_m2']),np.trace(low['shared_plane_parameter_covariance_m2']))
    def test_cancel_and_inconsistent_reused_receiver(self):
        data,bundle=fixture()
        self.assertEqual(infer_scene_bundle(data,bundle,cancel=lambda:True)['status'],'cancelled')
        data[1]['observations'][0]['receiver_position_m'][0]+=.01
        out=infer_scene_bundle(data,bundle)
        self.assertEqual(out['status'],'calibration_needed');self.assertIn('inconsistent survey',str(out['diagnostics']))


class ParentAlternativeTests(unittest.TestCase):
    def test_exact_corner_retains_real_extra_reflector_alternative(self):
        from echosight.multisource import _parent_subset_alternatives
        s=np.array([1.2,1.1,.9]);rng=np.random.default_rng(8932)
        receivers=rng.uniform([.7,.6,.3],[3.8,3.4,2.8],(8,3));sources=np.tile(s,(8,1))
        qs=[image_source(s,[1,0,0],0),image_source(s,[0,1,0],0),np.array([-s[0],-s[1],s[2]])]
        rows=[];links=[]
        for i,r in enumerate(receivers):
            peaks=[dict(candidate_id=f'{i}-{k}',delay_s=float(excess_delay(s,r,q,343)),delay_std_s=2e-5) for k,q in enumerate(qs)]
            rows.append(dict(source_index=0,session_id='fixed-source',o=dict(capture_id=str(i),direct_std_s=2e-5,receiver_position_std_m=.003),peaks=peaks,t=np.array([p['delay_s'] for p in peaks])))
            links.extend((k,i,k) for k in range(3))
        out=dict(surfaces=[dict(surface_id=f'plane{k}') for k in range(3)],hypotheses=[],diagnostics=[],guidance=[])
        _parent_subset_alternatives(out,qs,s,sources,receivers,343.,rows,links,np.diag([.003**2]*3+[.3**2]),np.eye(9)*.001**2,None)
        self.assertEqual(len(out['surfaces']),2)
        self.assertEqual(len(out['hypotheses'][0]['surfaces']),3)
        self.assertFalse(out['parent_model_comparison']['absence_established'])
        competing=out['hypotheses'][1]
        self.assertEqual(len(competing['surfaces']),2)
        self.assertTrue(any(e['reflection_order']==2 for e in competing['path_evidence']))
        self.assertEqual(len(competing['path_evidence']),len(links))
        # A genuinely coincident diagonal reflector produces the exact same
        # delays here; the three-plane interpretation must remain available.
        self.assertIn('possible',out['hypotheses'][0]['reason'])

    def test_genuine_additional_plane_is_retained(self):
        data,bundle=fixture()
        for item in data:
            s=np.array(item['session']['source_position_m'])
            for o in item['observations']:
                q=image_source(s,[1,0,0],4.)
                o['candidates'].append(dict(candidate_id=o['capture_id']+'-interior',delay_s=float(excess_delay(s,o['receiver_position_m'],q,343)),delay_std_s=2e-5,amplitude=1.))
        out=infer_scene_bundle(data,bundle)
        self.assertEqual(len(out['surfaces']),7,out['diagnostics'])
        self.assertTrue(any(abs(p['normal'][0])>.99 and abs(abs(p['offset_m'])-4)<.01 for p in out['surfaces']))
