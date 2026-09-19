"""Prepare licensed measured-RIR replay from an already retrieved FLAIR subset."""
import argparse,hashlib,json
from pathlib import Path
from run import ROOT
from evaluation.flair import prepare
from echosight.storage import load_session
p=argparse.ArgumentParser();p.add_argument('--subset',required=True);a=p.parse_args();destination=ROOT/'raw/flair'
if (destination/'session.json').exists():raise FileExistsError(destination)
prepare(a.subset,destination);session=load_session(destination/'session.json');target=next(x for x in json.loads((ROOT/'combination-input-manifest.json').read_text()) if x['suite']=='flair')
hashes={c['capture_id']:hashlib.sha256(Path(c['recording_path']).read_bytes()).hexdigest() for c in session['captures']}
assert hashes==target['recordings'];print('All24 measured-RIR hybrid WAVs match the executed trial')
