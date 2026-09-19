import argparse,json,hashlib
from pathlib import Path
from echosight import signals
p=argparse.ArgumentParser();p.add_argument('--estimator',choices=['matched_filter','joint_kernel'],required=True);p.add_argument('--suite',choices=['eight','twelve','stress','flair'],required=True);p.add_argument('--output',required=True);p.add_argument('--subset');a=p.parse_args()
original=signals.process_recording
def process(*args,**kwargs):
 kwargs['estimator']=a.estimator
 return original(*args,**kwargs)
signals.process_recording=process
if a.suite in ['eight','twelve']:
 from evaluation.run import run
 result=run(a.output,extended=a.suite=='twelve')
elif a.suite=='stress':
 from evaluation.stress import run
 result=run(a.output)
else:
 from evaluation.flair import run
 result=run(a.subset,a.output)
Path(a.output,'estimator-manifest.json').write_text(json.dumps(dict(estimator=a.estimator,suite=a.suite,driver_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()),indent=2)+'\n')
print(json.dumps(dict(estimator=a.estimator,suite=a.suite,passed=result['passed'],failures=result.get('required_failures'))))
