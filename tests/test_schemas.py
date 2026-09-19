"""Published structural contracts exercised with examples and actual outputs.

Semantic acoustic and raw-byte checks remain the runtime's responsibility.
Install requirements-test.txt for the formal JSON Schema validator.
"""
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from jsonschema import Draft202012Validator, ValidationError
from referencing import Registry, Resource
from tests.test_acquisition import capture_bytes

ROOT=Path(__file__).resolve().parents[1]
def validator(name):
    registry=Registry()
    for path in (ROOT/'schemas').glob('*.json'):
        schema=json.loads(path.read_text());resource=Resource.from_contents(schema)
        registry=registry.with_resource(schema['$id'],resource)
    return Draft202012Validator(json.loads((ROOT/'schemas'/f'{name}.schema.json').read_text()),registry=registry)

class SchemaTests(unittest.TestCase):
    def test_published_schemas_and_frontend_examples(self):
        for path in (ROOT/'schemas').glob('*.json'):
            with self.subTest(schema=path.name):Draft202012Validator.check_schema(json.loads(path.read_text()))
        contracts={'session':'session','controlled-request':'controlled-request','controlled-change':'controlled-result','ambiguous':'result','no-result':'result','reflector-partial':'result','room-partial':'result'}
        for name,schema in contracts.items():
            with self.subTest(example=name):validator(schema).validate(json.loads((ROOT/'examples/frontend'/f'{name}.json').read_text()))

    def test_capture_manifest_structural_boundaries(self):
        raw,_,_=capture_bytes()
        with zipfile.ZipFile(io.BytesIO(raw)) as z:manifest=json.loads(z.read('manifest.json'))
        check=validator('capture-manifest');check.validate(manifest)
        for mutate in (lambda m:m.update(sample_rate_hz=True),lambda m:m['continuity']['blocks'][0].update(sample_time=0),lambda m:m['continuity']['blocks'][0].update(host_time_valid=False),lambda m:m.update(recording_sha256='bad')):
            invalid=copy.deepcopy(manifest);mutate(invalid)
            with self.assertRaises(ValidationError):check.validate(invalid)
        interrupted=copy.deepcopy(manifest);interrupted['continuity']['status']='interrupted'
        check.validate(interrupted)  # valid evidence is not eligible geometry input

    def test_actual_raw_pipeline_outputs_and_job_match_contract(self):
        from echosight.simulation import simulate_session
        from echosight.storage import load_session,SessionStore
        from echosight.pipeline import process_session
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);session=load_session(simulate_session(root/'room',seed=1,capture_count=12))
            validator('session').validate(session)
            validator('result').validate(process_session(session))
            validator('result').validate(process_session({'session_id':'missing','captures':[]}))
            with SessionStore(root/'store') as store:
                sid=store.create_session({})['session_id']
                job=store.start_job(sid,process_session)
                validator('job').validate(job)

if __name__=='__main__':unittest.main()
