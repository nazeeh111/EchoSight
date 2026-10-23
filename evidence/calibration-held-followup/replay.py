"""Replay saved arithmetic only. Never renders audio, extracts arrivals or fits maps."""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent

def read(path):
    def reject(token):
        raise ValueError(f'Nonfinite JSON: {token}')
    value = json.loads(Path(path).read_text(), parse_constant=reject)
    def finite(x):
        if isinstance(x, float) and not math.isfinite(x):
            raise ValueError('Nonfinite JSON number')
        if isinstance(x, dict):
            for item in x.values(): finite(item)
        elif isinstance(x, list):
            for item in x: finite(item)
    finite(value)
    return value

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def verify(folder, entries):
    for name, digest in entries.items():
        if sha(folder / name) != digest:
            raise ValueError(f'Input identity changed: {folder / name}')

def compare(got, expected, path='$'):
    if isinstance(expected, dict):
        if not isinstance(got, dict) or got.keys() != expected.keys(): raise ValueError(path)
        for key in expected: compare(got[key], expected[key], f'{path}.{key}')
    elif isinstance(expected, list):
        if not isinstance(got, list) or len(got) != len(expected): raise ValueError(path)
        for i, (a,b) in enumerate(zip(got,expected)): compare(a,b,f'{path}[{i}]')
    elif isinstance(expected, float):
        if isinstance(got,bool) or not isinstance(got,(int,float)) or not math.isfinite(got) or not math.isclose(got,expected,rel_tol=1e-10,abs_tol=1e-12):
            raise ValueError((path,got,expected))
    elif type(got) is not type(expected) or got != expected:
        raise ValueError((path,got,expected))

def load(path, name):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

def recompute(repo):
    manifest=read(HERE/'manifest.json');verify(HERE,manifest['package_sha256'])
    original=repo/'evidence/calibration-room-transfer/replay'
    if sha(original/'manifest.json') != manifest['original_manifest_sha256']:
        raise ValueError('Original replay manifest changed')
    old_manifest=read(original/'manifest.json')
    verify(original,old_manifest['package_sha256']);verify(repo,old_manifest['repo_sha256'])
    # Recompute all inherited geometry, admission/timing and original failure gates first.
    gates=load(original/'frozen_gates.py','original_transfer_gates')
    gates.P=original;gates.ROOT=repo;gates.read=read
    gates.cfg=lambda:read(original/'settings.json')
    captured=[];gates.save=lambda path,value:captured.append(value)
    gates.summarize()
    if len(captured)!=1: raise ValueError('Original evaluator output count')
    inherited=captured[0]
    compare(inherited,read(original/'expected-results.json'))
    followup=load(HERE/'frozen_followup.py','frozen_followup')
    followup.P=HERE;followup.cfg=lambda:read(HERE/'records/settings.json')
    followup.base=lambda:original;followup.load_module=load
    followup.read=lambda path: inherited if Path(path)==original/'expected-results.json' else read(path)
    identities=read(HERE/'source-identities.json')['files']
    # Saved full-extraction identity is retained attribution, not a hash of reduced bytes.
    followup.sha=lambda path:identities['work/held-followup/extractions/'+Path(path).name]['sha256']
    extractions={seed:read(HERE/'extractions'/f'{seed}.json') for seed in followup.cfg()['seeds']}
    got=followup.summarize(extractions)
    # No expected follow-up numerical values are supplied until arithmetic completes.
    compare(got,read(HERE/'expected-results.json'))
    return {'comparison_passed':True,'rows_compared':len(got['rows']),
            'required_paths':sum(row['withheld']['expected'] for row in got['rows']),
            'original_rows_compared':len(inherited['rows']),
            'original_transfer_pass':inherited['transfer_pass'],
            'original_promotion_criteria_pass':inherited['promotion_criteria_pass'],
            'manifest_sha256':sha(HERE/'manifest.json'),
            'scope':'Saved-output arithmetic only. No audio, extraction, calibration, mapping or fresh timing. Full extraction and WAV hashes are recorded identities; omitted bytes cannot be independently verified here.',
            'tolerance':{'relative':1e-10,'absolute':1e-12,'gates_identifiers_structure':'exact'},'results':got}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo',type=Path,default=HERE.parent.parent,help='Repository checkout; defaults to this evidence folder\'s checkout')
    parser.add_argument('--output',type=Path,required=True,help='New JSON output path; existing entries, including symlinks, are refused')
    args=parser.parse_args()
    if args.output.exists() or args.output.is_symlink(): raise FileExistsError(args.output)
    result=recompute(args.repo.resolve())
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x') as stream:
        json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps({'comparison_passed':True,'rows_compared':result['rows_compared'],'required_paths':result['required_paths'],'transfer_pass':result['results']['transfer_pass'],'promotion_criteria_pass':result['results']['promotion_criteria_pass'],'output':str(args.output)}))

if __name__=='__main__':
    main()
