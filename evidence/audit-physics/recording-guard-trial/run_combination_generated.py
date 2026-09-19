"""Run unchanged combination driver on regenerated, hash-verified inputs."""
import run_combination as run
original=run.cases
def generated():
 rows=[]
 for suite,case,spec,folder,estimator in original():
  name=f"{case.get('scenario',case.get('family'))}-{case['seed']}"
  path=run.ROOT/'raw/flair' if suite=='flair' else run.ROOT/'raw'/suite/name
  rows.append((suite,case,spec,path,estimator))
 return rows
run.cases=generated
run.main()
