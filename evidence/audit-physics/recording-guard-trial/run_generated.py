"""Run the unchanged paired driver on regenerated, hash-verified raw inputs."""
import run
original=run.cases
def generated():
 rows=[]
 for suite,case,spec,folder,estimator in original():
  name=f"{case.get('scenario',case.get('family'))}-{case['seed']}"
  rows.append((suite,case,spec,run.ROOT/'raw'/suite/name,estimator))
 return rows
run.cases=generated
run.main()
