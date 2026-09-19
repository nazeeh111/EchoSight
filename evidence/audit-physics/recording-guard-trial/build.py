import hashlib,io,json,subprocess,tarfile
from pathlib import Path
root=Path(__file__).resolve().parent;snapshot=root/'snapshot';snapshot.mkdir(exist_ok=True)
commit='198d365f3b13f221ac258332eaaccdf96506a641'
archive=subprocess.check_output(['git','archive',commit,'echosight','evaluation','pyproject.toml','requirements.txt','requirements-evaluation.txt'])
with tarfile.open(fileobj=io.BytesIO(archive)) as tar:tar.extractall(snapshot,filter='data')
(snapshot/'EVALUATED_COMMIT').write_text(commit+'\n')
base=(snapshot/'echosight/inference.py').read_text();start=base.index("        if progress:progress(.1,'Generating image-source hypotheses')",base.index('def _run('));end=base.index("        if progress:progress(.55,'Assigning exclusive reflector evidence')",start)
replacement="""        refined=_held_select(session,observations,s,v,rows,r,out,cancel)
        if refined is None:
            out['diagnostics'].append('held_guard_unavailable_minimum_twelve_independent_valid_views')
            return out
"""
base=base[:start]+replacement+base[end:]
needle="        score,assign,meta=_score(qs,s,r,v,rows,session);pcov,e,cov,J=meta"
base=base.replace(needle,"        qs=_joint_refit(qs,s,r,v,rows,session,out,cancel)\n"+needle,1)
needle="        out['surfaces']=[_surface(q,k,assign,pcov,s,r,v,rows,session) for k,q in enumerate(qs)]"
base=base.replace(needle,needle+"\n        _attach_validation(out,qs,pcov)",1)
base=base.replace("        if prepared is None:return out\n        s,v,rows,r=prepared\n        refined=", "        if prepared is None:\n            out['held_guard']=dict(status='unavailable',reason='insufficient_valid_independent_views',calibrated=False)\n            return out\n        s,v,rows,r=prepared\n        refined=",1)
(snapshot/'echosight/guard_inference.py').write_text(base+'\n'+(root/'guard_helpers.py').read_text())
(snapshot/'echosight/joint_trial_signals.py').write_bytes((root/'frozen_joint_signals.py').read_bytes())
(snapshot/'echosight/joint_kernel.py').write_bytes((root/'frozen_joint_kernel.py').read_bytes())
(root/'snapshot-manifest.json').write_text(json.dumps(dict(commit=commit,files={str(p.relative_to(snapshot)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ['echosight','evaluation'] for p in sorted((snapshot/folder).glob('*.py'))}),indent=2)+'\n')
