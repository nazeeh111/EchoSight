#!/usr/bin/env python3
"""One-shot clean GitHub reproduction, invoked only with coordinator's final SHA."""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import zipfile

BASE = Path(__file__).resolve().parent
CHECKOUT = BASE / 'checkout'
PYTHON = BASE.parent / 'reproduction-venv' / 'bin' / 'python'
parser = argparse.ArgumentParser()
parser.add_argument('commit', help='exact final runtime commit supplied by coordinator')
args = parser.parse_args()
if not re.fullmatch('[0-9a-f]{40}', args.commit):
    parser.error('provide a full lowercase 40-character commit SHA')
OUT = BASE / ('evidence-' + args.commit[:12])
OUT.mkdir(exist_ok=False)
commands = []
started = time.time()


def save(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def run(label, command, timeout=300):
    print('START ' + label, flush=True)
    beginning = time.monotonic()
    env = dict(os.environ)
    env.pop('PYTHONPATH', None)
    with (OUT / (label + '.txt')).open('w') as stream:
        result = subprocess.run([str(item) for item in command], cwd=CHECKOUT,
            stdout=stream, stderr=subprocess.STDOUT, env=env, timeout=timeout)
    entry = {'label': label, 'argv': [str(item) for item in command], 'cwd': str(CHECKOUT),
        'exit_code': result.returncode, 'elapsed_s': time.monotonic() - beginning}
    commands.append(entry)
    save('commands.json', commands)
    print('END ' + label + ' exit=' + str(result.returncode), flush=True)
    if result.returncode:
        raise RuntimeError('Command failed; inspect ' + label + '.txt')
    return (OUT / (label + '.txt')).read_text().strip()


try:
    run('fetch', ['git', 'fetch', 'origin', 'backend/implementation'])
    run('remote-reachability', ['git', 'merge-base', '--is-ancestor', args.commit, 'origin/backend/implementation'])
    run('checkout', ['git', 'checkout', '--detach', args.commit])
    head = run('head', ['git', 'rev-parse', 'HEAD'])
    assert head == args.commit
    assert run('clean-before', ['git', 'status', '--porcelain']) == ''
    run('remote', ['git', 'remote', 'get-url', 'origin'])
    environment = run('environment', [PYTHON, '-c',
        'import sys,platform,json,importlib.metadata as m;'
        'print(json.dumps({"executable":sys.executable,"python":sys.version,"platform":platform.platform(),'
        '"packages":{p:m.version(p) for p in ("numpy","scipy","jsonschema","attrs","jsonschema-specifications","referencing","rpds-py","typing-extensions")}},indent=2))'])
    installed = json.loads(environment)['packages']
    for requirement_file in ('requirements.txt', 'requirements-test.txt'):
        for line in (CHECKOUT / requirement_file).read_text().splitlines():
            if '==' in line:
                name, version = line.split('==')
                assert installed[name] == version, (name, installed[name], version)
    # The exclusive evidence directory prevents accidental repeated full-suite runs.
    (OUT / 'full-suite-started').write_text(args.commit + '\n')
    run('full-suite', [PYTHON, '-m', 'unittest', 'discover', '-s', 'tests', '-v'], timeout=600)
    demo = OUT / 'demo'
    archive = OUT / 'room.zip'
    replay_store = OUT / 'replay-store'
    replay_result = OUT / 'replayed-result.json'
    run('demo', [PYTHON, '-m', 'echosight', 'demo', demo, '--seed', '1', '--captures', '12'])
    run('inspect', [PYTHON, '-m', 'echosight', 'inspect', demo / 'result.json'])
    run('export', [PYTHON, '-m', 'echosight', 'export', demo / 'session.json', '--output', archive])
    run('replay', [PYTHON, '-m', 'echosight', 'replay', archive, '--store', replay_store, '--output', replay_result])
    # Validate the newly generated artifacts directly, in addition to suite examples.
    from jsonschema import Draft202012Validator
    from referencing import Registry, Resource
    registry = Registry()
    schemas = {}
    for path in (CHECKOUT / 'schemas').glob('*.json'):
        schema = json.loads(path.read_text())
        registry = registry.with_resource(schema['$id'], Resource.from_contents(schema))
        schemas[path.stem.removesuffix('.schema')] = schema
    def validate(name, value):
        Draft202012Validator(schemas[name], registry=registry).validate(value)
    session = json.loads((demo / 'session.json').read_text())
    original = json.loads((demo / 'result.json').read_text())
    replay = json.loads(replay_result.read_text())
    validate('session', session)
    validate('result', original)
    validate('result', replay)
    assert len(session['captures']) == 12
    assert len(original['surfaces']) == len(replay['surfaces']) == 6
    assert any(abs(surface['normal'][2]) > .9 for surface in original['surfaces'])
    assert original['surfaces'] == replay['surfaces']
    assert original['result_id'] == replay['result_id']
    assert original['provenance']['physical_validation'] is False
    assert replay['provenance']['physical_validation'] is False
    hashes = {capture['capture_id']: hashlib.sha256((demo / capture['recording_path']).read_bytes()).hexdigest()
        for capture in session['captures']}
    with zipfile.ZipFile(archive) as z:
        saved = json.loads(z.read('session.json'))
        validate('session', saved)
        validate('result', json.loads(z.read('result.json')))
        for capture in saved['captures']:
            assert hashlib.sha256(z.read(capture['recording_path'])).hexdigest() == hashes[capture['capture_id']]
    assert {item['capture_id']: item['sha256'] for item in replay['recording_manifest']} == hashes
    job_count = 0
    for path in (replay_store / 'jobs').glob('job_*.json'):
        if path.name.endswith(('.input.json', '.result.json')):
            continue
        validate('job', json.loads(path.read_text()))
        job_count += 1
    assert job_count == 1
    save('artifact-checks.json', {'status': 'passed', 'captures': len(hashes), 'surfaces': 6,
        'height_dependent_structure': True, 'raw_sha256': hashes, 'archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
        'result_id': original['result_id'], 'replay_result_id': replay['result_id'],
        'exact_geometry_equal': True, 'generated_session_result_and_job_schemas': 'passed',
        'physical_validation': False})
    assert run('clean-after', ['git', 'status', '--porcelain']) == ''
    file_hashes = {}
    for root_name in ('echosight', 'tests', 'schemas'):
        for path in sorted((CHECKOUT / root_name).rglob('*')):
            if path.is_file() and '__pycache__' not in path.parts:
                file_hashes[str(path.relative_to(CHECKOUT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    for relative in ('README.md', 'docs/API.md', 'docs/FRONTEND_HANDOFF.md', 'requirements.txt', 'requirements-test.txt'):
        file_hashes[relative] = hashlib.sha256((CHECKOUT / relative).read_bytes()).hexdigest()
    save('source-sha256.json', file_hashes)
    save('summary.json', {'status': 'passed', 'commit': args.commit, 'remote': 'https://github.com/nazeeh111/EchoSight.git',
        'checkout': str(CHECKOUT), 'started_at': started, 'elapsed_s': time.time() - started,
        'full_suite_runs': 1, 'environment_reused': str(PYTHON), 'new_dependencies': False,
        'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'commands': commands,
        'limitations': ['Synthetic CLI geometry, not own-device validation.',
            'Existing pinned environment reused; this does not test fresh network dependency installation.',
            'Scientific failed acceptance reports are preserved; ordinary test passing does not erase them.']})
    print('PASSED ' + str(OUT), flush=True)
except BaseException as error:
    save('failure.json', {'status': 'failed', 'commit': args.commit, 'error': repr(error), 'commands': commands})
    raise
