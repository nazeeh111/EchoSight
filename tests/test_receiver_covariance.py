"""Receiver-array covariance checks independent of selected plane labels."""
import copy
import unittest
from unittest.mock import patch
import numpy as np
from echosight import multisource as ms
from echosight import path_alternatives as pa
from tests.test_multisource import fixture


def declaration(data, covariance):
    groups=list(dict.fromkeys(o['receiver_pose_group_id'] for p in data for o in p['observations']))
    return dict(group_ids=groups,covariance_m2=np.asarray(covariance).tolist(),
                assumption='independent_of_source_and_effective_speed',scalar_policy='replace')


class ReceiverCovarianceTests(unittest.TestCase):
    def test_rigid_array_projection_matches_finite_difference_and_monte_carlo(self):
        rng=np.random.default_rng(62811)
        positions=np.array([[1,.2,.6],[1.2,.1,.7],[.8,.3,.5],[1.1,.4,.8]])
        origin=positions.mean(axis=0);s=np.array([.1,.6,.3]);q=np.array([-.1,.6,.3]);v=343.
        def skew(x):return np.array([[0,-x[2],x[1]],[x[2],0,-x[0]],[-x[1],x[0],0]])
        B=np.vstack([np.column_stack([np.eye(3),-skew(r-origin)]) for r in positions])
        rigid=np.diag([.002**2]*3+[.004**2]*3)
        C=B@rigid@B.T+np.eye(12)*.0002**2
        data,bundle=fixture(receivers=4)
        config=declaration(data,C);bundle['shared_calibration']['receiver_pose_covariance']=config
        calibration=ms._receiver_calibration(bundle,data)
        # Repeat all capsules at a second source; they retain the same survey draw.
        sources=np.repeat([s,s+[.2,.1,.3]],4,axis=0);receivers=np.tile(positions,(2,1))
        images=sources.copy();images[:,0]*=-1
        def delay(r):return (np.linalg.norm(r-images,axis=-1)-np.linalg.norm(r-sources,axis=-1))/v
        gradients=np.empty((8,3))
        for axis in range(3):
            h=np.eye(3)[axis]*1e-6
            gradients[:,axis]=(delay(receivers+h)-delay(receivers-h))/(2e-6)
        groups=config['group_ids']*2
        projected=ms._receiver_projection(groups,gradients,np.full(8,900.),calibration)
        D=np.zeros((8,12))
        for i,g in enumerate(groups):D[i,3*config['group_ids'].index(g):3*config['group_ids'].index(g)+3]=gradients[i]
        np.testing.assert_allclose(projected,D@C@D.T,rtol=1e-12,atol=1e-20)
        perturb=rng.multivariate_normal(np.zeros(12),C,size=40000).reshape(-1,4,3)
        ys=delay(receivers[None]+np.tile(perturb,(1,2,1)))
        empirical=np.cov(ys,rowvar=False)
        self.assertLess(np.linalg.norm(empirical-projected)/np.linalg.norm(projected),.025)
        # Common projected 20 mm translation does not average to 20/sqrt(5).
        common=dict(index={str(i):i for i in range(5)},covariance=np.kron(np.ones((5,5)),np.eye(3)*.02**2))
        joint=ms._receiver_projection(list(common['index']),np.tile([1.,0,0],(5,1)),np.zeros(5),common)
        self.assertAlmostEqual(float(np.ones(5)@joint@np.ones(5)/25),.02**2)
        independent=ms._receiver_projection(list(common['index']),np.tile([1.,0,0],(5,1)),np.full(5,.02),None)
        self.assertAlmostEqual(float(np.ones(5)@independent@np.ones(5)/25),.02**2/5)

    def test_validation_before_proposals_and_no_mutation(self):
        data,bundle=fixture();bundle['shared_calibration']['receiver_pose_covariance']=declaration(data,np.eye(24)*.002**2)
        before=copy.deepcopy((data,bundle));calibration=ms._receiver_calibration(bundle,data)
        self.assertEqual(calibration['covariance'].shape,(24,24));self.assertEqual((data,bundle),before)
        malformed=[]
        for key,value in [('group_ids',['r0']*8),('group_ids',['r0']*65),('group_ids',['r0',*['r'+str(i) for i in range(1,7)],'x'*161]),('group_ids',['r'+str(i) for i in range(7)]+['extra']),('covariance_m2',[[0]]),('assumption','unknown'),('scalar_policy','add')]:
            bad=copy.deepcopy(bundle);bad['shared_calibration']['receiver_pose_covariance'][key]=value;malformed.append(bad)
        for entry in [True,'0',float('nan'),float('inf'),10**1000]:
            bad=copy.deepcopy(bundle);bad['shared_calibration']['receiver_pose_covariance']['covariance_m2'][0][0]=entry;malformed.append(bad)
        bad=copy.deepcopy(bundle);bad['shared_calibration']['receiver_pose_covariance']['covariance_m2'][0][0]=-.01;malformed.append(bad)
        bad=copy.deepcopy(bundle);bad['shared_calibration']['receiver_pose_covariance']['covariance_m2'][0][1]=.001;malformed.append(bad)
        with patch.object(ms.single,'_proposals',side_effect=AssertionError('invalid declaration reached fitting')):
            for bad in malformed:
                result=ms.infer_scene_bundle(data,bad)
                self.assertEqual(result['status'],'calibration_needed',result)
                self.assertEqual(result['surfaces'],[])
        self.assertEqual(ms.infer_scene_bundle(data,bundle,cancel=lambda:True)['status'],'cancelled')

    def test_full_diagonal_equivalent_legacy_and_explicit_scalar_replacement(self):
        data,bundle=fixture();before=copy.deepcopy(data)
        baseline=ms.infer_scene_bundle(data,bundle)
        bundle['shared_calibration']['receiver_pose_covariance']=declaration(data,np.eye(24)*.002**2)
        result=ms.infer_scene_bundle(data,bundle)
        self.assertEqual(result['surfaces'],baseline['surfaces'])
        np.testing.assert_allclose(result['shared_plane_parameter_covariance_m2'],baseline['shared_plane_parameter_covariance_m2'],atol=1e-15)
        self.assertEqual(data,before)
        for a,item in enumerate(data):
            for o in item['observations']:o['receiver_position_std_m']=.04+a*.01
        replaced=ms.infer_scene_bundle(data,bundle)
        self.assertEqual(replaced['surfaces'],result['surfaces'])
        self.assertEqual(replaced['receiver_pose_uncertainty']['scalar_policy'],'replace')

    def test_actual_point_and_fixed_plane_use_full_array_and_keep_source_terms(self):
        data,bundle=fixture(receivers=4);v,source_cov=ms._calibration(bundle,4)
        C=np.kron(np.ones((4,4)),np.eye(3)*.003**2)+np.eye(12)*.001**2
        bundle['shared_calibration']['receiver_pose_covariance']=declaration(data,C)
        receiver=ms._receiver_calibration(bundle,data)
        support=[dict(session_id=item['session']['session_id'],capture_id=o['capture_id'],candidate_id=o['candidates'][0]['candidate_id']) for item in data for o in item['observations']]
        surface=dict(normal=[1.,0,0],offset_m=0.,support=support)
        rows,s,r,y,v,fixed,mu,q=pa._evidence(surface,data,v,source_cov,receiver)
        zero=copy.deepcopy(receiver);zero['covariance']=np.zeros_like(C)
        fixed_zero=pa._evidence(surface,data,v,source_cov,zero)[5]
        u=(q-r)/np.linalg.norm(q-r,axis=1)[:,None];u0=(s-r)/np.linalg.norm(s-r,axis=1)[:,None]
        expected=ms._receiver_projection([row['group'] for row in rows],(u0-u)/v,np.zeros(len(rows)),receiver)
        np.testing.assert_allclose(fixed-fixed_zero,expected,rtol=1e-12,atol=1e-20)
        p=np.array([2.,2.,2.]);actual=pa._point_nuisance_covariance(p,rows,s,r,v,source_cov,receiver)
        actual_zero=pa._point_nuisance_covariance(p,rows,s,r,v,source_cov,zero)
        # Independent numerical receiver derivative for the physical point path.
        gradient=np.empty_like(r)
        for axis in range(3):
            h=np.eye(3)[axis]*1e-6
            gradient[:,axis]=(pa.prediction(p,s,r+h,v)-pa.prediction(p,s,r-h,v))/(2e-6)
        expected=ms._receiver_projection([row['group'] for row in rows],gradient,np.zeros(len(rows)),receiver)
        np.testing.assert_allclose(actual-actual_zero,expected,rtol=1e-7,atol=1e-20)
        J=pa.derivatives(p,s,r,v)[0]
        sandwich=pa._fixed_weight_covariance(J,fixed,actual)
        W=np.linalg.inv(fixed);L=np.linalg.solve(J.T@W@J,J.T@W)
        np.testing.assert_allclose(sandwich,L@actual@L.T,rtol=1e-10,atol=1e-16)

    def test_plane_covariance_matches_independent_full_nuisance_projection(self):
        data,bundle=fixture(receivers=4);v,cal=ms._calibration(bundle,4)
        R=np.kron(np.ones((4,4)),np.eye(3)*.009**2)+np.eye(12)*.001**2
        bundle['shared_calibration']['receiver_pose_covariance']=declaration(data,R)
        receiver=ms._receiver_calibration(bundle,data)
        rows=[];sources=[];positions=[]
        for a,item in enumerate(data):
            for o in item['observations']:
                rows.append(dict(source_index=a,receiver_group=o['receiver_pose_group_id'],o=o,peaks=o['candidates'],t=np.array([p['delay_s'] for p in o['candidates']])))
                sources.append(item['session']['source_position_m']);positions.append(o['receiver_position_m'])
        sources=np.array(sources);positions=np.array(positions);reference=sources[0];q=reference*np.array([-1,1,1]);links=[(0,i,0) for i in range(len(rows))]
        covariance,rank,_=ms._covariance([q],reference,sources,positions,v,rows,links,cal,receiver)
        def fixed_plane(s,r,speed):
            image=s*np.array([-1,1,1])
            return (np.linalg.norm(image-r,axis=1)-np.linalg.norm(s-r,axis=1))/speed
        base=fixed_plane(sources,positions,v);J=np.empty((len(rows),3));A=np.zeros((len(rows),13));D=np.zeros((len(rows),12))
        for axis in range(3):
            h=np.eye(3)[axis]*1e-5
            J[:,axis]=(ms._predict(q+h,reference,sources,positions,v)[0]-ms._predict(q-h,reference,sources,positions,v)[0])/2e-5
        for a in range(4):
            source_mask=np.array([row['source_index']==a for row in rows])
            group_mask=np.array([row['receiver_group']=='r'+str(a) for row in rows])
            for axis in range(3):
                h=np.eye(3)[axis]*1e-5
                A[:,3*a+axis]=(fixed_plane(sources+source_mask[:,None]*h,positions,v)-fixed_plane(sources-source_mask[:,None]*h,positions,v))/2e-5
                D[:,3*a+axis]=(fixed_plane(sources,positions+group_mask[:,None]*h,v)-fixed_plane(sources,positions-group_mask[:,None]*h,v))/2e-5
        A[:,-1]=(fixed_plane(sources,positions,v+1e-4)-fixed_plane(sources,positions,v-1e-4))/2e-4
        C=A@cal@A.T+D@R@D.T+np.eye(len(rows))*(2*(2e-5)**2)
        L=np.linalg.pinv(J)
        np.testing.assert_allclose(covariance,L@C@L.T,rtol=1e-8,atol=1e-15)
        self.assertEqual(rank,3)
        # Parent gates use each receiver's true marginal; cross-capsule blocks
        # also reach their fitted parent uncertainty through covariance above.
        gradient=np.array([[1.,2.,3.],[3.,1.,2.]])
        groups=['r0','r3']
        np.testing.assert_allclose(ms._receiver_marginal(groups,gradient,[999,999],receiver),np.diag(ms._receiver_projection(groups,gradient,[0,0],receiver)))

    def test_nonlinear_plane_refits_preserve_rigid_array_uncertainty(self):
        from scipy.optimize import least_squares
        from scipy.spatial.transform import Rotation
        data,bundle=fixture(receivers=4);sources=np.array([item['session']['source_position_m'] for item in data])
        positions=np.array([o['receiver_position_m'] for o in data[0]['observations']]);origin=positions.mean(axis=0)
        def skew(x):return np.array([[0,-x[2],x[1]],[x[2],0,-x[0]],[-x[1],x[0],0]])
        B=np.vstack([np.column_stack([np.eye(3),-skew(r-origin)]) for r in positions])
        sigma=np.array([.002]*3+[.001]*3);C=B@np.diag(sigma**2)@B.T+np.eye(12)*.0002**2
        bundle['shared_calibration']['receiver_pose_covariance']=declaration(data,C);receiver=ms._receiver_calibration(bundle,data)
        rows=[]
        for a,item in enumerate(data):
            for o in item['observations']:
                o=copy.deepcopy(o);o['direct_std_s']=1e-7
                for peak in o['candidates']:peak['delay_std_s']=1e-7
                rows.append(dict(source_index=a,receiver_group=o['receiver_pose_group_id'],o=o,peaks=o['candidates'],t=np.array([p['delay_s'] for p in o['candidates']])))
        s=np.repeat(sources,4,axis=0);r=np.tile(positions,(4,1));reference=sources[0];q=reference*np.array([-1,1,1]);links=[(0,i,0) for i in range(16)]
        predicted=ms._covariance([q],reference,s,r,343.,rows,links,np.zeros((13,13)),receiver)[0]
        rng=np.random.default_rng(62821);fits=[]
        for _ in range(600):
            delta=rng.normal(size=6)*sigma
            actual=Rotation.from_rotvec(delta[3:]).apply(positions-origin)+origin+delta[:3]+rng.normal(0,.0002,(4,3))
            actual=np.tile(actual,(4,1));images=s*np.array([-1,1,1])
            y=(np.linalg.norm(images-actual,axis=1)-np.linalg.norm(s-actual,axis=1))/343.
            fit=least_squares(lambda x:(ms._predict(x,reference,s,r,343.)[0]-y)*343.,q,max_nfev=30)
            self.assertTrue(fit.success);fits.append(fit.x)
        empirical=np.cov(fits,rowvar=False)
        self.assertLess(np.linalg.norm(empirical-predicted)/np.linalg.norm(predicted),.15)

    def test_raw_entry_keeps_matrix_and_recording_bytes_and_validates_before_read(self):
        import tempfile,hashlib
        from pathlib import Path
        from scipy.io import wavfile
        data,bundle=fixture();bundle['shared_calibration']['receiver_pose_covariance']=declaration(data,np.eye(24)*.002**2)
        with tempfile.TemporaryDirectory() as tmp:
            raw=copy.deepcopy(bundle);raw['sessions']=[];paths=[];digests=[]
            for a,item in enumerate(data):
                session=copy.deepcopy(item['session']);session['captures']=[];session['probe']={}
                for i,o in enumerate(item['observations']):
                    path=Path(tmp)/f'{a}-{i}.wav';wavfile.write(path,48000,np.array([a*8+i+1,0,-1,0],dtype=np.int16))
                    paths.append(path);digests.append(hashlib.sha256(path.read_bytes()).hexdigest())
                    session['captures'].append(dict(capture_id=o['capture_id'],receiver_position_m=o['receiver_position_m'],receiver_position_std_m=.002,receiver_pose_group_id=o['receiver_pose_group_id'],recording_path=str(path)))
                raw['sessions'].append(session)
            original=copy.deepcopy(raw)
            # Real WAV admission, deterministic detector fixture isolates covariance
            # transport from waveform detection (which has separate raw tests).
            with patch('echosight.signals.process_recording',side_effect=[copy.deepcopy(o) for item in data for o in item['observations']]):
                result=ms.process_scene_bundle(raw)
            self.assertEqual(len(result['surfaces']),6,result['diagnostics'])
            self.assertEqual(result['receiver_pose_uncertainty']['covariance_m2'],raw['shared_calibration']['receiver_pose_covariance']['covariance_m2'])
            self.assertEqual(raw,original)
            self.assertEqual([hashlib.sha256(path.read_bytes()).hexdigest() for path in paths],digests)
            self.assertEqual([o['recording_sha256'] for item in result['processed_sessions'] for o in item['observations']],digests)
            prepared=ms.infer_scene_bundle(result['processed_sessions'],raw)
            self.assertEqual(prepared['surfaces'],result['surfaces'])
            raw['shared_calibration']['receiver_pose_covariance']['group_ids'][-1]='missing'
            with patch('echosight.storage.read_recording_evidence_snapshot',side_effect=AssertionError('invalid covariance read WAV')):
                invalid=ms.process_scene_bundle(raw)
            self.assertIn('exactly cover',str(invalid['diagnostics']));self.assertEqual(invalid['surfaces'],[])
            self.assertEqual(ms.process_scene_bundle(original,cancel=lambda:True)['status'],'cancelled')

    def test_declared_and_observed_positions_must_agree_even_for_rejected_capture(self):
        data,bundle=fixture();bundle['shared_calibration']['receiver_pose_covariance']=declaration(data,np.eye(24)*.002**2)
        data[1]['observations'][0]['status']='rejected';data[1]['observations'][0]['receiver_position_m'][0]+=.1
        result=ms.infer_scene_bundle(data,bundle)
        self.assertIn('inconsistent survey position',str(result['diagnostics']))
        self.assertEqual(result['surfaces'],[])
        data,bundle=fixture();bundle['shared_calibration']['receiver_pose_covariance']=declaration(data,np.eye(24)*.002**2)
        o=data[0]['observations'][0]
        data[0]['session']['captures']=[dict(capture_id=o['capture_id'],receiver_position_m=o['receiver_position_m'],receiver_pose_group_id='other')]
        result=ms.infer_scene_bundle(data,bundle)
        self.assertIn('receiver group disagree',str(result['diagnostics']))

if __name__=='__main__':unittest.main()
