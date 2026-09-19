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

    def test_near_parallel_dimension_translation_invariant(self):
        """A two-degree pair has no unique global distance; use a stated line."""
        import copy
        session,observations,_=fixture()
        source=np.asarray(session['source_position_m']);angle=np.deg2rad(2.)
        planes=[(np.array([1.,0.,0.]),0.),(np.array([np.cos(angle),np.sin(angle),0.]),4.7)]
        for row in observations:
            row['candidates']=[dict(candidate_id=f"{row['capture_id']}-{j}",delay_s=float(excess_delay(source,row['receiver_position_m'],image_source(source,n,d),343)),delay_std_s=1e-5,amplitude=1.) for j,(n,d) in enumerate(planes)]
        original=infer_scene(session,observations)
        shifted_session=copy.deepcopy(session);shifted_observations=copy.deepcopy(observations)
        shift=np.array([17.,100.,-31.])
        shifted_session['source_position_m']=(source+shift).tolist()
        for row in shifted_observations:row['receiver_position_m']=(np.array(row['receiver_position_m'])+shift).tolist()
        shifted=infer_scene(shifted_session,shifted_observations)
        self.assertEqual(len(original['dimensions']),1)
        a,b=original['dimensions'][0],shifted['dimensions'][0]
        self.assertAlmostEqual(a['value_m'],b['value_m'],places=7)
        self.assertAlmostEqual(a['std_m'],b['std_m'],places=7)
        np.testing.assert_allclose(a['reference_point_m'],source,atol=1e-8)
        np.testing.assert_allclose(np.array(b['intersection_points_m'])-shift,a['intersection_points_m'],atol=1e-7)
        mean=(planes[0][0]+planes[1][0]);mean/=np.linalg.norm(mean)
        distances=[(d-n@source)/(n@mean) for n,d in planes]
        self.assertAlmostEqual(a['value_m'],abs(distances[1]-distances[0]),places=7)
        reference_sensitivity=planes[0][0]/(planes[0][0]@mean)-planes[1][0]/(planes[1][0]@mean)
        self.assertAlmostEqual(a['reference_std_bound_m'],session['source_position_std_m']*np.linalg.norm(reference_sensitivity),places=9)
        self.assertGreaterEqual(a['std_m'],a['geometry_std_m'])

    def test_parallel_dimension_has_no_reference_location_term(self):
        session,observations,_=fixture()
        out=infer_scene(session,observations)
        self.assertEqual(len(out['dimensions']),3)
        for dimension in out['dimensions']:
            self.assertLess(dimension['reference_std_bound_m'],1e-10)
            self.assertAlmostEqual(dimension['std_m'],dimension['geometry_std_m'],places=9)

    def test_double_bounce_not_a_definitive_diagonal_wall(self):
        """Coherent higher-order paths can fit a nonexistent plane exactly."""
        rng=np.random.default_rng(9021);source=np.array([1.7,1.2,1.1])
        positions=rng.uniform([.6,.5,.3],[3.8,3.4,2.7],(12,3))
        session=dict(session_id='double-bounce',source_position_m=source.tolist(),source_position_std_m=.003,sound_speed_m_s=343.,sound_speed_std_m_s=.2,source_clock_std_ppm=50)
        images=[image_source(source,[1,0,0],0),image_source(source,[0,1,0],0),image_source(source,[0,0,1],3.4),np.array([-1.7,-1.2,1.1])]
        observations=[dict(capture_id=str(i),status='ok',receiver_position_m=r.tolist(),receiver_position_std_m=.003,direct_std_s=2e-5,candidates=[dict(candidate_id=f'{i}-{j}',delay_s=float(excess_delay(source,r,q,343)),delay_std_s=2e-5,amplitude=1) for j,q in enumerate(images)]) for i,r in enumerate(positions)]
        out=infer_scene(session,observations)
        self.assertEqual(out['status'],'ambiguous')
        self.assertEqual(out['surfaces'],[])
        explanations=out['higher_order_explanations']
        self.assertEqual(len(explanations),1)
        self.assertEqual(len(explanations[0]['support']),12)
        fewer=next(h for h in out['hypotheses'] if h['hypothesis_id']=='fewer_surfaces_with_second_order_paths')
        self.assertEqual(len(fewer['surfaces']),3)
        # A real coincident diagonal reflector is observationally identical:
        # preserve the four-reflector interpretation rather than asserting absence.
        original=next(h for h in out['hypotheses'] if h['hypothesis_id']=='first_order_reflector_interpretation')
        self.assertEqual(len(original['surfaces']),4)
        guidance=next(g for g in out['guidance'] if g.get('action')=='move_source_for_reflection_order_discrimination')
        self.assertGreater(guidance['predicted_median_delay_separation_s'],1e-5)
        self.assertEqual(guidance['receiver_only_discrimination_possible'],False)

    def test_higher_order_does_not_hide_receiver_mirror(self):
        rng=np.random.default_rng(9021);source=np.array([1.7,1.2,1.1])
        positions=rng.uniform([.6,.5,.3],[3.8,3.4,2.7],(12,3));positions[:,2]=1.1
        session=dict(session_id='combined',source_position_m=source.tolist(),source_position_std_m=.003,sound_speed_m_s=343.,sound_speed_std_m_s=.2)
        images=[image_source(source,[1,0,0],0),image_source(source,[0,1,0],0),image_source(source,[0,0,1],3.4),np.array([-1.7,-1.2,1.1])]
        observations=[dict(capture_id=str(i),status='ok',receiver_position_m=r.tolist(),receiver_position_std_m=.003,direct_std_s=2e-5,candidates=[dict(candidate_id=f'{i}-{j}',delay_s=float(excess_delay(source,r,q,343)),delay_std_s=2e-5,amplitude=1) for j,q in enumerate(images)]) for i,r in enumerate(positions)]
        out=infer_scene(session,observations)
        self.assertEqual(out['surfaces'],[])
        self.assertIn('first_order_vs_higher_order_ambiguity',out['diagnostics'])
        self.assertIn('support_coplanar_mirror_ambiguity',out['diagnostics'])
        self.assertIn('coplanar_mirror',[h['hypothesis_id'] for h in out['hypotheses']])
        self.assertTrue(any(g.get('action')=='move_source_for_reflection_order_discrimination' for g in out['guidance']))
        self.assertTrue(any('height' in g.get('action','') for g in out['guidance']))

    def test_two_bounce_path_obeys_reflection_law(self):
        from echosight.geometry import reflection_path
        source=np.array([1.7,1.2,1.1]);receiver=np.array([2.6,.8,2.])
        planes=[(np.array([1.,0,0]),0.),(np.array([0.,1,0]),0.)]
        paths=[reflection_path(source,receiver,order) for order in (planes,planes[::-1])]
        self.assertEqual(sum(p is None for p in paths),1)
        path=next(p for p in paths if p is not None)
        self.assertEqual(len(path['vertices_m']),4)
        expected=np.linalg.norm(receiver-np.array([-1.7,-1.2,1.1]))
        self.assertAlmostEqual(path['length_m'],expected,places=10)
        self.assertLess(path['max_reflection_law_error'],1e-10)

    def test_unobserved_parent_planes_leave_order_unresolved(self):
        session,observations,_=fixture()
        source=np.array(session['source_position_m']);double=np.array([-source[0],-source[1],source[2]])
        for row in observations:
            row['candidates']=[dict(candidate_id=row['capture_id']+'-double',delay_s=float(excess_delay(source,row['receiver_position_m'],double,343)),delay_std_s=1e-5,amplitude=1.)]
        out=infer_scene(session,observations)
        self.assertEqual(len(out['surfaces']),1)
        self.assertEqual(out.get('higher_order_explanations',[]),[])
        surface=out['surfaces'][0]
        self.assertEqual(surface['model_status'],'conditional_first_order_hypothesis')
        self.assertIn('reflection_order',surface['uncertainty']['excluded_model_errors'])

    def test_joint_calibration_covariance_matches_numerical_derivative(self):
        from echosight.inference import _covariance
        session,observations,_=fixture();s=np.array(session['source_position_m']);v=346.
        n=np.array([1.,0,0]);d=4.7;q=image_source(s,n,d)
        factor=np.array([[.002,0,0,0],[.0008,.0015,0,0],[0,.0003,.001,0],[.04,0,.02,.15]])
        joint=factor@factor.T
        session.update(effective_speed_m_s=v,source_effective_speed_covariance=joint.tolist(),source_position_std_m=99.,sound_speed_std_m_s=99.,source_clock_std_ppm=100000.)
        r=np.array([o['receiver_position_m'] for o in observations[:3]])
        rows=[]
        for i,receiver in enumerate(r):
            peak=dict(candidate_id=str(i),delay_s=float(excess_delay(s,receiver,q,v)),delay_std_s=1e-5)
            rows.append(dict(o=dict(direct_std_s=0.,receiver_position_std_m=0.),r=receiver,t=np.array([peak['delay_s']]),peaks=[peak]))
        _,covariance,_=_covariance([q],[(0,i,0) for i in range(3)],s,r,v,rows,session)
        values=np.r_[s,v];jac=np.zeros((3,4));eps=1e-5
        for axis in range(4):
            plus=values.copy();minus=values.copy();plus[axis]+=eps;minus[axis]-=eps
            def predict(theta):return excess_delay(theta[:3],r,image_source(theta[:3],n,d),theta[3])
            jac[:,axis]=(predict(plus)-predict(minus))/(2*eps)
        np.testing.assert_allclose(covariance,jac@joint@jac.T+np.eye(3)*1e-10,rtol=1e-7,atol=1e-15)

    def test_effective_speed_is_not_relabelled_physical_sound_speed(self):
        session,observations,_=fixture();session['effective_speed_m_s']=346.
        session['source_effective_speed_covariance']=np.diag([1e-6,1e-6,1e-6,.01]).tolist()
        for row in observations:
            for peak in row['candidates']:peak['delay_s']*=343/346
        result=infer_scene(session,observations)
        self.assertEqual(len(result['surfaces']),6)
        self.assertLess(max(abs(e['residual_s']) for p in result['surfaces'] for e in p['support']),1e-7)
        bad=dict(session,source_effective_speed_covariance=np.diag([1.,1.,1.,-1.]).tolist())
        self.assertEqual(infer_scene(bad,observations)['status'],'no_result')
        missing=dict(session);del missing['source_effective_speed_covariance']
        self.assertEqual(infer_scene(missing,observations)['status'],'no_result')

    def test_nearly_symmetric_indefinite_calibration_is_rejected(self):
        session,observations,_=fixture();matrix=np.eye(4)
        matrix[0,1]=1+1e-9;matrix[1,0]=1.
        # It meets entrywise symmetry tolerance and raw eigvalsh(lower triangle)
        # is PSD, but the actually used symmetrized covariance is indefinite.
        session.update(effective_speed_m_s=343.,source_effective_speed_covariance=matrix.tolist())
        self.assertEqual(infer_scene(session,observations)['status'],'no_result')
