from pathlib import Path
import json,hashlib,collections
import numpy as np
from scipy.optimize import linear_sum_assignment
root=Path("/Users/nazeeh/Documents/Codex/2026-09-18/echosight-autonomous-backend-implementation-lead-a/backend")
work=root/"work/spatial-finish"; source=root.parent/"work/clean-checkout/work/relocation-heldout-de8442b"
criteria=json.loads((root/"evaluation/source_relocation_acceptance.json").read_text());report=json.loads((work/"experiment-results.json").read_text());freeze=report["freeze"]
assert hashlib.sha256((work/"experimental_multisource.py").read_bytes()).hexdigest()==freeze["experimental_sha256"]
assert hashlib.sha256((root/"echosight/multisource.py").read_bytes()).hexdigest()==freeze["original_sha256"]
assert hashlib.sha256((root/"evaluation/source_relocation_acceptance.json").read_bytes()).hexdigest()==freeze["acceptance_sha256"]
assert {(x["family"],x["seed"]) for x in report["cases"]}=={(x["family"],x["seed"]) for x in criteria["cases"]}
rows=[]
for case in report["cases"]:
 name=f'{case["family"]}-{case["seed"]}';folder=source/name
 assert hashlib.sha256((folder/"mapper-result.json").read_bytes()).hexdigest()==case["input_sha256"]
 assert hashlib.sha256((folder/"bundle.json").read_bytes()).hexdigest()==case["bundle_sha256"]
 truth=json.loads((folder/"truth.json").read_text())["surfaces"]
 item={"case":name,"methods":{}}
 for method in ("original","experimental"):
  output=json.loads((work/f"{name}-{method}.json").read_text());pred=output["surfaces"];valid=np.zeros((len(pred),len(truth)),dtype=bool)
  for i,p in enumerate(pred):
   for j,t in enumerate(truth):
    dot=np.dot(p["normal"],t["normal"]);angle=np.rad2deg(np.arccos(np.clip(abs(dot)/(np.linalg.norm(p["normal"])*np.linalg.norm(t["normal"])),0,1)));offset=abs(p["offset_m"]-np.sign(dot)*t["offset_m"])
    valid[i,j]=angle<=5 and offset<=.15
  a,b=linear_sum_assignment(~valid);matched=int(valid[a,b].sum());saved=case["results"][method]["metrics"]
  assert [matched,len(pred)-matched,len(truth)-matched]==[saved["matched_count"],saved["false_surfaces"],saved["missed_surfaces"]]
  support=[];used=set()
  for p in pred:
   counts=collections.Counter();points=[]
   for e in p["support"]:
    key=(e["session_id"],e["capture_id"],e["candidate_id"]);assert key not in used;used.add(key);counts[e["session_id"]]+=1
   # Existing stored output links source/capture identity; independently find receiver positions.
   processed=json.loads((folder/"mapper-result.json").read_text())["processed_sessions"]
   poses={(s["session"]["session_id"],o["capture_id"]):o["receiver_position_m"] for s in processed for o in s["observations"]}
   points=np.array([poses[(e["session_id"],e["capture_id"])] for e in p["support"]]);rank=int(np.linalg.matrix_rank(points-points.mean(0),tol=1e-5))
   assert len(counts)==len(processed) and min(counts.values())>=4 and len(points)>=8 and rank==3
   support.append({"surface_id":p["surface_id"],"counts_by_source":dict(counts),"receiver_rank":rank})
  item["methods"][method]={"matched":matched,"false":len(pred)-matched,"missed":len(truth)-matched,"support":support,"status":output["status"]}
 rows.append(item)
result={"input_and_code_hashes_match":True,"all_12_frozen_cases_present":True,"independent_cardinality_counts_match":True,"all_definitive_surface_support_and_exclusive_candidate_checks_pass":True,"cases":rows,"scope":"Independent saved-output rescore and support check; no inference rerun or raw timing claim."}
out=Path(__file__).with_name("spatial-check.json");out.write_text(json.dumps(result,indent=2)+"\n");print(json.dumps({k:v for k,v in result.items() if k!="cases"},indent=2))
