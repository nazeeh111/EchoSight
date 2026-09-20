#!/usr/bin/env python3
"""Fresh GitHub material-feature reproduction; requires coordinator's final SHA."""
import argparse
import hashlib
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
REMOTE = 'https://github.com/nazeeh111/EchoSight.git'
parser = argparse.ArgumentParser()
parser.add_argument('commit', help='full final pushed commit supplied by coordinator')
args = parser.parse_args()
if not re.fullmatch('[0-9a-f]{40}', args.commit):
    parser.error('provide a full lowercase 40-character SHA')
if CHECKOUT.exists():
    parser.error('checkout already exists; do not reuse or overwrite a reproduction checkout')
OUT = BASE / ('evidence-' + args.commit[:12])
OUT.mkdir(exist_ok=False)
commands = []
started = time.time()


def save(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(label, command, timeout=300, cwd=None):
    print('START ' + label, flush=True)
    beginning = time.monotonic()
    env = dict(os.environ)
    env.pop('PYTHONPATH', None)
    argv = [str(item) for item in command]
    with (OUT / (label + '.txt')).open('w') as stream:
        result = subprocess.run(argv, cwd=cwd or CHECKOUT, stdout=stream,
            stderr=subprocess.STDOUT, env=env, timeout=timeout)
    commands.append({'label': label, 'argv': argv, 'cwd': str(cwd or CHECKOUT),
        'exit_code': result.returncode, 'elapsed_s': time.monotonic() - beginning})
    save('commands.json', commands)
    print('END ' + label + ' exit=' + str(result.returncode), flush=True)
    if result.returncode:
        raise RuntimeError('Command failed; inspect ' + label + '.txt')
    return (OUT / (label + '.txt')).read_text().strip()


try:
    run('clone', ['git', 'clone', '--single-branch', '--branch', 'backend/implementation',
        '--no-checkout', REMOTE, CHECKOUT], cwd=BASE)
    run('remote-head', ['git', 'rev-parse', 'origin/backend/implementation'])
    # Preserve exact-commit reproduction after the default branch advances.
    run('target-on-remote', ['git', 'merge-base', '--is-ancestor', args.commit, 'origin/backend/implementation'])
    run('checkout', ['git', 'checkout', '--detach', args.commit])
    assert run('head', ['git', 'rev-parse', 'HEAD']) == args.commit
    assert run('clean-before', ['git', 'status', '--porcelain']) == ''
    assert run('remote', ['git', 'remote', 'get-url', 'origin']) == REMOTE
    environment = json.loads(run('environment', [PYTHON, '-c',
        'import sys,platform,json,importlib.metadata as m,echosight;'
        'print(json.dumps({"executable":sys.executable,"python":sys.version,"platform":platform.platform(),'
        '"echosight_file":echosight.__file__,"packages":{p:m.version(p) for p in '
        '("numpy","scipy","jsonschema","attrs","jsonschema-specifications","referencing","rpds-py","typing-extensions")}},indent=2))']))
    assert Path(environment['echosight_file']).resolve().is_relative_to(CHECKOUT)
    for requirement_file in ('requirements.txt', 'requirements-test.txt'):
        for line in (CHECKOUT / requirement_file).read_text().splitlines():
            if '==' in line:
                name, version = line.split('==')
                assert environment['packages'][name] == version, (name, version)
    (OUT / 'full-suite-started').write_text(args.commit + '\n')
    suite = run('full-suite', [PYTHON, '-m', 'unittest', 'discover', '-s', 'tests', '-v'], timeout=900)
    count = re.search(r'Ran (\d+) tests in ([0-9.]+)s', suite)
    assert count is not None and suite.rstrip().endswith('OK'), 'Missing successful suite summary'

    demo = OUT / 'room-demo'
    run('room-demo', [PYTHON, '-m', 'echosight', 'demo', demo, '--seed', '1', '--captures', '12'])
    run('room-inspect', [PYTHON, '-m', 'echosight', 'inspect', demo / 'result.json'])
    plain = read(demo / 'result.json')
    assert len(plain['surfaces']) == 6
    assert any(abs(surface['normal'][2]) > .9 for surface in plain['surfaces'])
    assert plain['provenance']['physical_validation'] is False

    material = OUT / 'material-demo'
    run('material-demo', [PYTHON, '-m', 'evaluation.material_development', '--output', material])
    material_report = read(material / 'summary.json')
    assert material_report['status'] == 'passed'
    assert material_report['checks'] and all(material_report['checks'].values())
    assert material_report['physical_validation'] is False
    context = read(material / 'context.json')
    material_result = read(material / 'room-result.json')
    cli_result_path = OUT / 'material-cli-result.json'
    run('material-process-context', [PYTHON, '-m', 'echosight', 'process', material / 'room/session.json',
        '--interpretation-context', material / 'context.json', '--output', cli_result_path])
    cli_result = read(cli_result_path)
    assert cli_result['result_id'] == material_result['result_id']
    assert cli_result['surfaces'] == material_result['surfaces']
    assert cli_result['interpretation'] == material_result['interpretation']
    assert cli_result['acquisition']['interpretation_context'] == context
    inspected = json.loads(run('material-inspect', [PYTHON, '-m', 'echosight', 'inspect', cli_result_path]))
    assert inspected['interpretation']['context_id'] == material_result['interpretation']['context_id']
    assert len(inspected['interpretation']['surface_interpretations']) == len(material_result['surfaces'])
    assert all('feature_records' not in item for item in inspected['interpretation']['surface_interpretations'])

    # Rebuild a known reference through the public raw CLI, reusing declared metadata.
    profile = read(material / 'flat_reflector-profile.json')
    save('profile-provenance.json', profile['provenance'])
    save('profile-appearance.json', profile['appearance'])
    reference = read(material / 'reference_flat-result.json')
    rebuilt_path = OUT / 'rebuilt-profile.json'
    run('material-reference', [PYTHON, '-m', 'echosight', 'material-reference', material / 'reference_flat/session.json',
        '--surface-id', reference['surfaces'][0]['surface_id'], '--material-id', profile['material_id'],
        '--label', profile['label'], '--route-id', profile['route_id'],
        '--provenance', OUT / 'profile-provenance.json', '--appearance', OUT / 'profile-appearance.json',
        '--prior-weight', profile['prior_weight'], '--regularization-std-db', profile['reference_summary']['regularization_std_db'],
        '--output', rebuilt_path])
    rebuilt = read(rebuilt_path)
    assert rebuilt == profile

    # Existing pinned validator, canonical local schema registry; no network lookup.
    from jsonschema import Draft202012Validator
    from referencing import Registry, Resource
    registry = Registry()
    schemas = {}
    for path in (CHECKOUT / 'schemas').glob('*.json'):
        schema = read(path)
        Draft202012Validator.check_schema(schema)
        registry = registry.with_resource(schema['$id'], Resource.from_contents(schema))
        schemas[path.stem.removesuffix('.schema')] = schema
    def validate(name, value):
        Draft202012Validator(schemas[name], registry=registry).validate(value)
    validate('interpretation-context', context)
    validate('interpretation-context', dict(context, profiles=[rebuilt]))
    validate('result', plain)
    for path in material.glob('*-result.json'):
        value = read(path)
        validate('result', value)
        validate('interpretation-result', value['interpretation'])
    validate('result', cli_result)

    archives = {}
    for name, session_path, original in [('room', demo / 'session.json', plain),
        ('material', material / 'room/with-context.json', material_result)]:
        session = read(session_path)
        validate('session', session)
        archive = OUT / (name + '.zip')
        replay_store = OUT / (name + '-replay-store')
        replay_path = OUT / (name + '-replayed-result.json')
        run(name + '-export', [PYTHON, '-m', 'echosight', 'export', session_path, '--output', archive])
        run(name + '-replay', [PYTHON, '-m', 'echosight', 'replay', archive, '--store', replay_store, '--output', replay_path])
        replay = read(replay_path)
        validate('result', replay)
        validate('interpretation-result', replay['interpretation'])
        assert replay['result_id'] == original['result_id']
        assert replay['surfaces'] == original['surfaces']
        assert replay['interpretation'] == original['interpretation']
        assert replay['provenance']['physical_validation'] is False
        hashes = {cap['capture_id']: sha(session_path.parent / cap['recording_path']) for cap in session['captures']}
        assert len(hashes) == 12
        with zipfile.ZipFile(archive) as z:
            saved = json.loads(z.read('session.json'))
            validate('session', saved)
            validate('result', json.loads(z.read('result.json')))
            if name == 'material':
                assert saved['interpretation_context'] == context
                assert replay['acquisition']['interpretation_context'] == context
                assert replay['interpretation']['context_id'] == material_result['interpretation']['context_id']
            for cap in saved['captures']:
                assert hashlib.sha256(z.read(cap['recording_path'])).hexdigest() == hashes[cap['capture_id']]
        assert {cap['capture_id']: cap['sha256'] for cap in replay['recording_manifest']} == hashes
        stored_session = read(replay_store / 'sessions' / session['session_id'] / 'session.json')
        assert stored_session['replay']['archived_result']['binding_issues'] == []
        assert stored_session['replay']['archived_result']['status'] == 'quarantined_unverified'
        job_count = 0
        for path in (replay_store / 'jobs').glob('job_*.json'):
            if path.name.endswith(('.input.json', '.result.json')):
                continue
            validate('job', read(path)); job_count += 1
        assert job_count == 1
        archives[name] = {'raw_sha256': hashes, 'archive_sha256': sha(archive),
            'result_id': replay['result_id'], 'context_id': replay['interpretation']['context_id'],
            'exact_geometry_and_interpretation_equal': True, 'archived_binding_issues': []}
    assert run('clean-after', ['git', 'status', '--porcelain']) == ''
    source_hashes = {}
    for folder in ('echosight', 'tests', 'schemas'):
        for path in sorted((CHECKOUT / folder).rglob('*')):
            if path.is_file() and '__pycache__' not in path.parts:
                source_hashes[str(path.relative_to(CHECKOUT))] = sha(path)
    for relative in ('evaluation/material_development.py', 'README.md', 'docs/USAGE.md', 'docs/API.md',
        'docs/MATERIALS_APPEARANCE.md', 'docs/FRONTEND_HANDOFF.md', 'pyproject.toml', 'requirements.txt', 'requirements-test.txt'):
        source_hashes[relative] = sha(CHECKOUT / relative)
    save('source-sha256.json', source_hashes)
    save('artifact-checks.json', {'status': 'passed', 'archives': archives,
        'rebuilt_reference_profile_exact_equal': True, 'reference_profile_sha256': sha(rebuilt_path),
        'material_demo_checks': material_report['checks'], 'unknown_material_surfaces': material_report['unknown_material_surfaces'],
        'offline_schemas': 'passed', 'physical_validation': False})
    save('summary.json', {'status': 'passed', 'commit': args.commit, 'remote': REMOTE,
        'checkout': str(CHECKOUT), 'suite_tests': int(count.group(1)), 'suite_reported_seconds': float(count.group(2)),
        'started_at': started, 'elapsed_s': time.time() - started, 'full_suite_runs': 1,
        'environment_reused': str(PYTHON), 'new_dependencies': False, 'runner_sha256': sha(__file__),
        'limitations': ['Controlled synthetic material profiles and supplied palettes, not physical classification or optical accuracy.',
            'Pinned environment reused; no fresh dependency installation or universal-platform claim.',
            'Existing failed scientific acceptance remains separate from passing software checks.']})
    print('PASSED ' + str(OUT), flush=True)
except BaseException as error:
    save('failure.json', {'status': 'failed', 'commit': args.commit, 'error': repr(error), 'commands': commands})
    raise
