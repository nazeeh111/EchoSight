import importlib.util,json,sys,time,unittest
from pathlib import Path
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root))
import echosight
spec=importlib.util.spec_from_file_location('echosight.multisource',root/'work/spatial-finish/experimental_multisource_v2.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);sys.modules['echosight.multisource']=mod;echosight.multisource=mod
suite=unittest.defaultTestLoader.loadTestsFromName('tests.test_multisource')
suite.addTests(unittest.defaultTestLoader.loadTestsFromName('tests.test_mapping_admission_cancellation.MultisourceAdmissionTests.test_joint_late_cancel_discards_all_derived_geometry_but_keeps_inputs'))
result=unittest.TextTestRunner(verbosity=2).run(suite)
(root/'work/review-spatial-pruning/suite-results.json').write_text(json.dumps({'testsRun':result.testsRun,'failures':[str(t)+': '+s for t,s in result.failures],'errors':[str(t)+': '+s for t,s in result.errors]},indent=2)+'\n')
assert result.wasSuccessful()
