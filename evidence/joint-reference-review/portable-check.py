"""Check committed portable projection and run committed adapter in isolation."""
from pathlib import Path
import hashlib,json,subprocess,sys,os
ROOT=Path(__file__).resolve().parents[2];OWN=ROOT/'work/review-joint-reference'
COMMIT='e372158d9daa47891b0c5f7106b224b0aca75d05';PKG=Path('evidence/joint-reference-trial')
sha=lambda b:hashlib.sha256(b).hexdigest()
read=lambda p:json.loads(p.read_text())
git=lambda *args:subprocess.check_output(['git',*args],cwd=ROOT)
files=git('ls-tree','-r','--name-only',COMMIT,str(PKG)).decode().splitlines()
clean=OWN/'portable-clean';clean.mkdir(exist_ok=True)
assert not list(clean.iterdir()),'Use fresh isolated destination; do not overwrite review evidence'
for path in files:
 data=git('show',f'{COMMIT}:{path}');assert data==(ROOT/path).read_bytes(),path
 target=clean/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
p=clean/PKG
manifest=read(p/'portable-manifest.json')
for group in ['required_sha256','supplementary_sha256']:
 for name,digest in manifest[group].items():assert sha((p/name).read_bytes())==digest,(group,name)
original_manifest=read(p/'MANIFEST.json')
for name,digest in original_manifest.items():
 assert sha((p/name).read_bytes())==digest,name
 # Only compare original trial files that existed in work; the original README was packaged later.
 if (ROOT/'work/joint-reference-trial'/name).is_file():assert (p/name).read_bytes()==(ROOT/'work/joint-reference-trial'/name).read_bytes(),name
assert sha((p/'freeze.json').read_bytes())=='1b59eb563ba72e29eebf1244a3eb59272e9d8c97f42eaa147d5bac5970e2b941'
assert (ROOT/'evidence/independent-review-joint-reference.md').read_bytes()==git('show',f'{COMMIT}:evidence/independent-review-joint-reference.md')
assert not git('diff','--name-only','38ce3ff',COMMIT,'--','echosight','tests').strip()
inputs=read(p/'portable-inputs.json');freeze=read(p/'freeze.json');admissions=read(p/'admission.json')
assert set(inputs)=={'scope','original_input_sha256','pairs'}
assert [x['seed'] for x in inputs['pairs']]==[2821,2833]
assert len(inputs['original_input_sha256'])==12
for name,digest in inputs['original_input_sha256'].items():assert sha((ROOT/name).read_bytes())==digest==freeze['input_hashes'][name],name
capture_keys={'capture_id','receiver_position_m','receiver_position_std_m','receiver_pose_group_id'}
observation_keys={'capture_id','status','direct_std_s','recording_sha256','waveform_sha256','clock'}
candidate_keys={'candidate_id','delay_s','delay_std_s'}
count=0
for pair in inputs['pairs']:
 assert set(pair)=={'pattern','seed','sessions','references','rows'} and pair['pattern']=='single'
 assert len(pair['sessions'])==len(pair['references'])==2 and len(pair['rows'])==24
 admission=next(a for a in admissions if a['seed']==pair['seed'] and a['pattern']=='single')
 assert admission['admitted']
 for j,plane in enumerate(['x','y']):
  raw=ROOT/f"work/source-calibration-mismatch/run-v2/raw/single-{pair['seed']}-{plane}"
  session=read(raw/'session.json');reference=read(raw/'reference.json');observations=read(raw/'observations.json')
  compact=pair['sessions'][j];assert set(compact)=={'source_position_m','sound_speed_m_s','source_clock_scale'}
  assert compact=={k:session[k] for k in compact}
  assert pair['references'][j]==reference
  caps={c['capture_id']:c for c in session['captures']};obs={o['capture_id']:o for o in observations['observations']}
  for i in range(12):
   cap,ob,ca=pair['rows'][j*12+i];a=admission['records'][j*12+i]
   assert set(cap)==capture_keys and set(ob)==observation_keys and set(ca)==candidate_keys
   assert set(ob['clock'])=={'alpha','alpha_std'}
   cid=f'capture-{i:02d}';assert cap['capture_id']==ob['capture_id']==a['capture_id']==cid
   assert cap=={k:caps[cid][k] for k in capture_keys}
   expected={k:obs[cid][k] for k in observation_keys};expected['clock']={k:obs[cid]['clock'][k] for k in ['alpha','alpha_std']}
   assert ob==expected
   original=next(c for c in obs[cid]['candidates'] if c['candidate_id']==a['candidate_id'])
   assert ca=={k:original[k] for k in candidate_keys}
   assert a['reference']==plane and a['partition']==('training' if i<8 else 'validation') and a['accepted']
   wav=f"work/source-calibration-mismatch/run-v2/raw/single-{pair['seed']}-{plane}/{cid}.wav"
   assert ob['recording_sha256']==freeze['input_hashes'][wav]
   count+=1
assert not (clean/'work/source-calibration-mismatch').exists()
# -I removes current directory and PYTHONPATH from import search; trial uses only supplied compact arrays.
execution=subprocess.run([sys.executable,'-I',str(p/'portable-replay.py'),'--output',str(OWN/'portable-isolated-result.json')],cwd=clean,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},capture_output=True,text=True)
(OWN/'portable-isolated.log').write_text(execution.stdout+execution.stderr)
assert execution.returncode==0,execution.stderr
actual=read(OWN/'portable-isolated-result.json');assert actual==read(p/'portable-result.json')
output=dict(commit=COMMIT,committed_package_files_matched=len(files),original_manifest_hashes_matched=len(original_manifest),portable_manifest_hashes_matched=sum(len(manifest[k]) for k in ['required_sha256','supplementary_sha256']),original_projected_file_hashes_matched=12,exact_projected_rows=count,runtime_and_tests_unchanged_from='38ce3ff',isolated_replay_exit_code=execution.returncode,isolated_replay=actual,original_tree_present=False)
(OWN/'portable-check.json').write_text(json.dumps(output,indent=2)+'\n');print(json.dumps(output,indent=2))
