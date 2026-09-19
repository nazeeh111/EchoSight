import unittest
from evaluation.metrics import score_surfaces, acceptance_failures

class EvaluationMetricsTests(unittest.TestCase):
    def test_orientation_invariance_and_exclusive_matching(self):
        p={'normal':[-1,0,0], 'offset_m':-2., 'surface_id':'p'}
        t={'normal':[1,0,0], 'offset_m':2., 'surface_id':'t'}
        score=score_surfaces({'surfaces':[p,p]}, {'surfaces':[t]})
        self.assertEqual(score['matched_count'],1)
        self.assertEqual(score['false_surfaces'],1)
        self.assertEqual(score['matches'][0]['offset_error_m'],0)

    def test_height_and_miss_are_reported(self):
        t=[{'normal':[0,0,1], 'offset_m':3.}, {'normal':[1,0,0], 'offset_m':4.}]
        score=score_surfaces({'surfaces':[t[0]]},{'surfaces':t})
        self.assertEqual(score['horizontal_matched'],1)
        self.assertEqual(score['missed_surfaces'],1)
        self.assertIsNone(score['matches'][0]['offset_95pct_covered'])

    def test_false_surface_cannot_match_just_by_distance(self):
        score=score_surfaces({'surfaces':[{'normal':[0,1,0], 'offset_m':2.}]},
                             {'surfaces':[{'normal':[1,0,0], 'offset_m':2.}]})
        self.assertEqual(score['matched_count'],0)
        self.assertEqual(score['false_surfaces'],1)
        self.assertEqual(score['missed_surfaces'],1)

    def test_null_failure_not_hidden_by_absence_of_truth(self):
        result={'status':'ok','surfaces':[{'normal':[1,0,0],'offset_m':1}]}
        score=score_surfaces(result,{'surfaces':[]})
        failures=acceptance_failures('null',result,score,0,{'requirements':{'null':{'maximum_false_surfaces':0,'allowed_status':['no_result']}}})
        self.assertEqual(len(failures),2)

if __name__=='__main__': unittest.main()
