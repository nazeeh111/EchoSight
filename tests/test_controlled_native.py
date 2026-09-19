"""Actual raw native metadata must constrain a controlled change claim."""
import copy
from pathlib import Path
import tempfile
import unittest
from evaluation.controlled_development import recording_protocol
from tests.test_acquisition import capture_bytes
from echosight.storage import read_recording
from echosight.controlled import process_controlled_protocol

class NativeControlledTests(unittest.TestCase):
    def test_raw_native_controls_cannot_be_overridden_by_outer_labels(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);original=recording_protocol(folder/'raw','moved',receiver_count=4)
            samples=[[read_recording(c['recording_path'])[0] for c in e['session']['captures']] for e in original['epochs']]
            for case in ('matching','configuration','input_route','source_route','probe','recorder','missing_evidence'):
                with self.subTest(case=case):
                    protocol=copy.deepcopy(original)
                    for a,epoch in enumerate(protocol['epochs']):
                        for i,capture in enumerate(epoch['session']['captures']):
                            if case=='missing_evidence' and a==1:continue
                            def mutate(m):
                                m['capture_id']=f'{a}-{i}'
                                m['source_declaration'].update(configuration_id=epoch['source_configuration_id'],probe_id='same-probe',route_id='same-output-route')
                                if a not in (1,2):return
                                if case=='configuration':m['source_declaration']['configuration_id']='different-source'
                                if case=='source_route':m['source_declaration']['route_id']='different-output'
                                if case=='probe':m['source_declaration']['probe_id']='different-probe'
                                if case=='recorder':m['recorder']['version']='changed-version'
                                if case=='input_route':
                                    m['route_initial'].update(input_port_type='USBAudio',input_port_name='changed-input')
                                    m['route_final']=copy.deepcopy(m['route_initial'])
                            raw,_,_=capture_bytes(samples[a][i],mutate)
                            path=folder/f'{case}-{a}-{i}.zip';path.write_bytes(raw);capture['recording_path']=str(path)
                    result=process_controlled_protocol(protocol)
                    if case=='matching':self.assertEqual(result['status'],'repeatable_acoustic_change_unlocalized',result['diagnostics'])
                    else:
                        self.assertEqual(result['status'],'inconclusive',result['diagnostics'])
                        self.assertFalse(result['receiver_evidence']);self.assertFalse(result['conditional_spatial_changes'])
                        self.assertIn('native_controls_contradict_protocol',str(result['diagnostics']))
                    self.assertFalse(result['physical_validation'])
                    self.assertEqual(len(result['epoch_results']),4) # retained evidence for diagnosis/reprocessing

if __name__=='__main__':unittest.main()
