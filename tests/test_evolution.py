import copy
import unittest


def result(surface_offset=2., count=4):
    return {"schema_version": "1.0", "result_id": "r", "status": "partial",
            "acquisition": {"coordinate_frame_id": "room-survey", "source_position_m": [0, 0, 1], "sound_speed_m_s": 343.,
                            "source_clock_scale": 1., "probe": {"probe_id": "p"}},
            "surfaces": [{"surface_id": "s", "normal": [1, 0, 0], "offset_m": surface_offset,
                          "support": [{"capture_id": str(i), "candidate_id": f"e{i}"} for i in range(count)]}],
            "observations": [{"capture_id": str(i)} for i in range(count)]}


class EvolutionTests(unittest.TestCase):
    def test_extra_views_preserve_track_and_explain_support(self):
        from echosight.evolution import compare_results
        a, b = result(), result(2.01, 7)
        b["surfaces"][0]["surface_id"] = "s-refined"
        out = compare_results(a, b)
        self.assertEqual(out["status"], "comparable")
        self.assertEqual(out["correspondences"][0]["track_id"], "s")
        self.assertEqual(out["correspondences"][0]["additional_support_count"], 3)
        self.assertEqual(out["new_capture_ids"], ["4", "5", "6"])

    def test_missing_surface_does_not_claim_physical_removal(self):
        from echosight.evolution import compare_results
        a, b = result(), result()
        b["surfaces"] = []
        out = compare_results(a, b)
        self.assertEqual(out["unconfirmed_previous_surface_ids"], ["s"])
        self.assertFalse(out["physical_scene_change_established"])

    def test_frame_or_probe_change_refuses_surface_comparison(self):
        from echosight.evolution import compare_results
        a, b = result(), result()
        b["acquisition"]["source_position_m"][2] = 1.2
        self.assertEqual(compare_results(a,b)["status"], "incomparable")
        del b["acquisition"]
        self.assertEqual(compare_results(a,b)["status"], "incomparable")

    def test_ambiguity_resolution_is_named_without_inventing_scene_change(self):
        from echosight.evolution import compare_results
        a, b = result(), result()
        a["status"] = "ambiguous"; a["surfaces"] = []
        a["hypotheses"] = [{}, {}]
        b["status"] = "ok"
        out = compare_results(a,b)
        self.assertTrue(out["ambiguity_reduced"])
        self.assertEqual(out["newly_supported_surface_ids"], ["s"])

    def test_malformed_geometry_is_rejected(self):
        from echosight.evolution import compare_results
        for broken in [[], {"surfaces": [None]}, {"surfaces": [{"normal": [0,0,0]}]}]:
            with self.subTest(broken=broken), self.assertRaises(ValueError):
                compare_results(result(), broken)
        broken = result(); broken["surfaces"][0]["normal"][0] = float("nan")
        with self.assertRaises(ValueError): compare_results(result(), broken)

    def test_unidentified_or_changed_coordinate_frame_is_incomparable(self):
        from echosight.evolution import compare_results
        a,b=result(),result();b["acquisition"]["coordinate_frame_id"]="different-room"
        self.assertEqual(compare_results(a,b)["status"],"incomparable")
        del a["acquisition"]["coordinate_frame_id"];del b["acquisition"]["coordinate_frame_id"]
        self.assertEqual(compare_results(a,b)["status"],"incomparable")

    def test_non_string_coordinate_frame_is_rejected(self):
        from echosight.evolution import compare_results
        a,b=result(),result()
        a["acquisition"]["coordinate_frame_id"]={"frame":"room"}
        b["acquisition"]["coordinate_frame_id"]={"frame":"room"}
        with self.assertRaises(ValueError): compare_results(a,b)

    def test_surface_tracking_is_invariant_to_coordinate_origin(self):
        import math
        from echosight.evolution import compare_results
        a,b=result(),result(2.01)
        b['surfaces'][0]['normal']=[math.cos(.035),math.sin(.035),0.]
        before=compare_results(a,b)
        self.assertEqual(len(before['correspondences']),1)
        for scene in (a,b):
            scene['acquisition']['source_position_m'][1]+=100
            for surface in scene['surfaces']:
                surface['offset_m']+=100*surface['normal'][1]
        after=compare_results(a,b)
        self.assertEqual(len(after['correspondences']),1)
        self.assertAlmostEqual(before['correspondences'][0]['offset_change_m'],after['correspondences'][0]['offset_change_m'])

    def test_effective_speed_change_is_incomparable(self):
        from echosight.evolution import compare_results
        a,b=result(),result()
        a['acquisition']['effective_speed_m_s']=343.
        b['acquisition']['effective_speed_m_s']=346.
        self.assertEqual(compare_results(a,b)['status'],'incomparable')


if __name__ == "__main__": unittest.main()
