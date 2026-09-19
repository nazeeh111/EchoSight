import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from .source_relocation_simulation import source_positions,corner_image,equivalent_plane,simulate

class SourceRelocationChecks(unittest.TestCase):
    def test_corner_alias_persists_along_intersection_and_changes_with_general_move(self):
        anchor=np.array([1.5,1.7,1.])
        for family in ['hidden_corner_fixed_sources','hidden_corner_tangential_sources']:
            planes=[equivalent_plane(s,corner_image(s)) for s in source_positions(anchor,family)]
            for normal,offset in planes[1:]:
                np.testing.assert_allclose(normal,planes[0][0]);self.assertAlmostEqual(offset,planes[0][1])
        poses=source_positions(anchor,'hidden_corner_four_sources')
        planes=[equivalent_plane(s,corner_image(s)) for s in poses]
        self.assertEqual(np.linalg.matrix_rank(poses[1:]-poses[0]),3)
        self.assertGreater(np.linalg.norm(planes[1][0]-planes[0][0]),.15)

    def test_bundle_preserves_shared_frame_and_receiver_survey_without_truth_leak(self):
        with tempfile.TemporaryDirectory() as folder:
            path=simulate(folder,'room_two_sources',1001)
            bundle=json.loads(path.read_text())
            sessions=[json.loads((path.parent/p).read_text()) for p in bundle['sessions']]
            self.assertEqual(len(sessions),2)
            for session in sessions:
                self.assertEqual(session['coordinate_frame_id'],bundle['coordinate_frame_id'])
                self.assertNotIn('truth',session);self.assertNotIn('surfaces',session)
            for a,b in zip(sessions[0]['captures'],sessions[1]['captures']):
                self.assertEqual(a['receiver_position_m'],b['receiver_position_m'])
                self.assertEqual(a['receiver_pose_group_id'],b['receiver_pose_group_id'])
            cov=np.asarray(bundle['shared_calibration']['source_pose_joint_covariance_m2'])
            self.assertEqual(cov.shape,(6,6));self.assertGreater(cov[0,3],0)
            self.assertGreater(np.linalg.eigvalsh(cov).min(),0)
            from echosight.storage import load_session
            for p in bundle['sessions']:self.assertEqual(len(load_session(path.parent/p)['captures']),12)

if __name__=='__main__':unittest.main()
