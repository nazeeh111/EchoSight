from pathlib import Path
import sys,json,numpy as np
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import waveform_v3 as w
s=np.array([[1.,0.,0.],[1.,0.,0.]]);r=np.array([[2.,0.,0.],[-1.,0.,0.]]);ref=np.array([1.,0.,0.]);p=np.array([-2.,0.,0.,0.]);delay,valid=w.delays(p,'plane',s,r,ref,343.);assert valid.tolist()==[True,False]
kernel=np.exp(-(w.TIME/.00004)**2);records=[dict(source=a,receiver=b,y=kernel) for a,b in zip(s,r)];res,gains,alignment=w.residual_profiles(p,'plane',records,kernel,ref,343.);assert np.max(abs(res))<1e-12 and gains[1,1]==0
positions=np.array([[0,0,0],[.75,0,0],[0,.75,0],[.15,.2,.6]]);allsv=np.linalg.svd(positions-positions.mean(axis=0),compute_uv=False);partsv=np.linalg.svd(positions[:3]-positions[:3].mean(axis=0),compute_uv=False);assert allsv[-1]>.03 and partsv[-1]<.03
result=dict(passed=True,opposite_side_plane_path_absent=True,absent_reflection_gain=float(gains[1,1]),max_null_residual=float(np.max(abs(res))),all_source_min_singular_m=float(allsv[-1]),three_supported_source_min_singular_m=float(partsv[-1]),scope='No generated recording or fitted truth used')
(HERE/'v3-math-checks.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
