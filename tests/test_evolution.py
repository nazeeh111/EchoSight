import copy
import unittest


def result(surface_offset=2., count=4):
    return {"schema_version": "1.0", "result_id": "r", "session_id": "session-a", "status": "partial",
            "acquisition": {"coordinate_frame_id": "room-survey", "source_position_m": [0, 0, 1], "sound_speed_m_s": 343.,
                            "source_clock_scale": 1., "probe": {"probe_id": "p"}},
            "surfaces": [{"surface_id": "s", "normal": [1, 0, 0], "offset_m": surface_offset,
                          "support": [{"capture_id": str(i), "candidate_id": f"e{i}"} for i in range(count)]}],
            "observations": [{"capture_id": str(i)} for i in range(count)]}


class EvolutionTests(unittest.TestCase):
    def test_cross_session_capture_names_do_not_erase_new_evidence(self):
        from echosight.evolution import compare_results
        a, b = result(), result()
        b['session_id'] = 'session-b'
        comparison = compare_results(a, b)
        self.assertEqual(comparison['new_capture_ids'], ['0', '1', '2', '3'])
        item = comparison['correspondences'][0]
        self.assertEqual(item['additional_support_count'], 4)
        self.assertEqual(item['lost_support_capture_ids'], ['0', '1', '2', '3'])
        self.assertEqual(item['additional_support_references'][0],
                         {'session_id': 'session-b', 'capture_id': '0'})
        self.assertEqual(item['lost_support_references'][0],
                         {'session_id': 'session-a', 'capture_id': '0'})
        self.assertFalse(comparison['physical_scene_change_established'])

    def test_missing_session_scope_does_not_claim_evidence_identity(self):
        from echosight.evolution import compare_results
        a, b = result(), result(count=7)
        del a['session_id']
        comparison = compare_results(a, b)
        self.assertEqual(comparison['support_comparison_status'], 'unavailable')
        self.assertIsNone(comparison['correspondences'][0]['additional_support_count'])
        self.assertEqual(comparison['new_capture_references'], [])
        self.assertEqual(comparison['new_capture_ids'], [])
        self.assertEqual(len(comparison['correspondences']), 1)

    def test_capture_scope_contradictions_and_duplicates_are_rejected(self):
        from echosight.evolution import compare_results
        invalid = result()
        invalid['acquisition']['session_id'] = 'contradicts-top-level'
        with self.assertRaises(ValueError): compare_results(invalid, result())
        invalid = result(); invalid['observations'].append(copy.deepcopy(invalid['observations'][0]))
        with self.assertRaises(ValueError): compare_results(invalid, result())
        for value in ('', True, 'x' * 161):
            invalid = result(); invalid['session_id'] = value
            with self.subTest(value=value), self.assertRaises(ValueError): compare_results(invalid, result())

    def test_tracks_carry_through_four_raw_revisions_without_mutation(self):
        from echosight.evolution import compare_results
        revisions=[]
        for i in range(4):
            item=result(2.+i*.01);item['result_id']=f'revision-{i}';item['surfaces'][0]['surface_id']=f'fit-{i}';revisions.append(item)
        originals=copy.deepcopy(revisions);carry=None
        for i in range(3):
            carry=compare_results(revisions[i],revisions[i+1],previous_comparison=carry)
            self.assertEqual(carry['current_tracks'],[{'surface_id':f'fit-{i+1}','track_id':'fit-0'}])
        self.assertEqual(revisions,originals)

    def test_birth_death_empty_intermediate_does_not_revive_a_track(self):
        from echosight.evolution import compare_results
        a,b,empty,c=[result() for _ in range(4)]
        for i,item in enumerate((a,b,empty,c)):item['result_id']=f'r{i}'
        b['surfaces'][0]['surface_id']='refit';empty['surfaces']=[]
        ab=compare_results(a,b);gone=compare_results(b,empty,previous_comparison=ab)
        self.assertEqual(gone['current_tracks'],[])
        reborn=compare_results(empty,c,previous_comparison=gone)
        self.assertEqual(reborn['correspondences'],[])
        self.assertEqual(reborn['newly_supported_surface_ids'],['s'])
        self.assertNotEqual(reborn['current_tracks'][0]['track_id'],'s')

    def test_born_surface_track_continues_when_an_older_surface_is_missing(self):
        from echosight.evolution import compare_results
        a,b,c=result(),result(),result()
        for name,item in zip(('a','b','c'),(a,b,c)):item['result_id']=name
        born=copy.deepcopy(b['surfaces'][0]);born.update(surface_id='born',normal=[0,1,0],offset_m=4.)
        b['surfaces'].append(born)
        c['surfaces']=[dict(copy.deepcopy(born),surface_id='born-refined',offset_m=4.01)]
        ab=compare_results(a,b);born_track=next(x['track_id'] for x in ab['current_tracks'] if x['surface_id']=='born')
        bc=compare_results(b,c,previous_comparison=ab)
        self.assertEqual(bc['current_tracks'],[{'surface_id':'born-refined','track_id':born_track}])
        self.assertEqual(bc['unconfirmed_previous_surface_ids'],['s'])

    def test_carry_is_bound_complete_unique_and_explicit(self):
        from echosight.evolution import compare_results
        a,b,c=result(),result(),result()
        a['result_id']='a';b['result_id']='b';c['result_id']='c'
        carry=compare_results(a,b)
        mutations=[lambda x:x.update(status='incomparable'),lambda x:x.update(current_result_id='stale'),
            lambda x:x.update(current_tracks=[]),lambda x:x['current_tracks'].append(copy.deepcopy(x['current_tracks'][0])),
            lambda x:x['current_tracks'][0].update(track_id=''),lambda x:x['current_tracks'][0].update(track_id='x'*161),
            lambda x:x['current_tracks'][0].update(surface_id='absent')]
        for mutate in mutations:
            invalid=copy.deepcopy(carry);mutate(invalid)
            with self.subTest(invalid=invalid),self.assertRaises(ValueError):compare_results(b,c,previous_comparison=invalid)
        previous=copy.deepcopy(b);previous.pop('result_id')
        with self.assertRaises(ValueError):compare_results(previous,c,previous_comparison=carry)
        b['surfaces'][0]['track_id']='conflicting-display-state'
        with self.assertRaises(ValueError):compare_results(b,c,previous_comparison=carry)
        two=copy.deepcopy(a);second=copy.deepcopy(a['surfaces'][0]);second['surface_id']='second';two['surfaces'].append(second)
        invalid={'schema_version':'1.0','status':'comparable','current_result_id':'a','current_tracks':[{'surface_id':'s','track_id':'same'},{'surface_id':'second','track_id':'same'}]}
        with self.assertRaises(ValueError):compare_results(two,c,previous_comparison=invalid)

    def test_result_identity_validation_and_collision_resolution(self):
        from echosight.evolution import compare_results
        for key,value in [('surface_id',''),('surface_id','x'*161),('track_id',None),('track_id',True)]:
            broken=result();broken['surfaces'][0][key]=value
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):compare_results(broken,result())
        duplicate=result();duplicate['surfaces']*=2
        with self.assertRaises(ValueError):compare_results(duplicate,result())
        tracks=result();second=copy.deepcopy(tracks['surfaces'][0]);second['surface_id']='other';second['track_id']='s';tracks['surfaces'].append(second)
        with self.assertRaises(ValueError):compare_results(tracks,result())
        a,b=result(),result();a['result_id']='a';b['result_id']='b'
        birth=copy.deepcopy(b['surfaces'][0]);birth.update(surface_id='new',normal=[0,1,0],offset_m=4.)
        b['surfaces'].append(birth)
        first=compare_results(a,b);born=next(t['track_id'] for t in first['current_tracks'] if t['surface_id']=='new')
        a['surfaces'][0]['track_id']=born
        collided=compare_results(a,b);tracks={x['surface_id']:x['track_id'] for x in collided['current_tracks']}
        self.assertEqual(tracks['s'],born);self.assertNotEqual(tracks['new'],born)
        self.assertEqual(collided,compare_results(a,b))

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
