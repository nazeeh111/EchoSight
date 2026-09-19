from pathlib import Path
import sys,json,copy,collections,numpy as np
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE));import waveform_v3 as w
out=HERE/'run-v3';sensitivity=json.loads((out/'sensitivity-results.json').read_text());analyses=[]
for index,row in enumerate(sensitivity['cases']):
 folder=out/'fresh'/f"{row['family']}-{row['seed']}";base=json.loads((folder/'baseline.json').read_text())['result'];bundle=json.loads((folder/'bundle.json').read_text());C=np.array(bundle['shared_calibration']['source_pose_joint_covariance_m2']);rng=np.random.default_rng(8101+index);nominal=w.prepare(base);perturbations=[]
 for draw in range(8):
  rng.multivariate_normal(np.zeros(12),C);rng.normal(0,.6)
  for i in range(12):rng.normal(0,.006,3)
  timed=copy.deepcopy(base);shifts=[];rate=[];normalizations=[]
  for item in timed['processed_sessions']:
   for o in item['observations']:
    if o['status']!='ok':continue
    shift=rng.normal(0,o['direct_std_s']);scale=1+rng.normal(0,o['clock']['alpha_std']/o['clock']['alpha']);shifts.append(shift);rate.append(scale-1);o['response']['start_delay_s']=o['response']['start_delay_s']*scale+shift;o['response']['sample_rate_hz']/=scale
    if int(o['capture_id'].split('-')[-1])<8:
     response=o['response'];y=np.array(response['values']);axis=response['start_delay_s']+np.arange(len(y))/response['sample_rate_hz'];normalizations.append(float(np.interp(0,axis,y)))
  p=w.prepare(timed);nominal_energy=float(np.sum(nominal[2]**2));ratio=None if p is None else float(np.sum(p[2]**2)/nominal_energy);perturbations.append(dict(draw=draw,record_count=len(shifts),outside_whole_mixture_alignment_domain=sum(abs(s)>2/48000 for s in shifts),max_reference_shift_us=max(abs(s) for s in shifts)*1e6,maximum_relative_rate_ppm=max(abs(e) for e in rate)*1e6,training_negative_zero_normalizers=sum(x<0 for x in normalizations),training_small_zero_normalizers=sum(abs(x)<.002 for x in normalizations),learned_kernel_energy_ratio=ratio))
 gates={}
 for kind in ['geometry_only','geometry_and_local_timing']:
  records=[d for d in row['draws'] if d['kind']==kind];counter=collections.Counter()
  for d in records:
   if d['status']=='unavailable':counter['unavailable']+=1;continue
   mse=d['held_mse'];params=d['parameters'];counts=d['component_held_support_counts'];msepass=mse['secondary']<=.7*min(mse['single'],mse['plane']);strongpass=sum(counts)>=12;boundary=any(abs(x)>.448 for x in params[:3]) or abs(params[3])>1.49
   if not msepass:counter['held_waveform_ratio_failed']+=1
   if not strongpass:counter['minimum12_strong_components_failed']+=1
   if boundary:counter['search_boundary_failed']+=1
   if not d['component_identifiable']:counter['component_support_or_conditioning_failed']+=1
   if not d['waveform_flag_before_identifiability'] and msepass and strongpass and not boundary:counter['held_record_improvement_gate_failed_by_elimination']+=1
   counter['source_flags']+=int(d['source_flag'])
  gates[kind]=dict(counter)
 analyses.append(dict(family=row['family'],seed=row['seed'],gates=gates,perturbations=perturbations))
(out/'sensitivity-diagnosis.json').write_text(json.dumps(analyses,indent=2)+'\n')
for r in analyses:
 if r['family'] in ['dual_room','dual_phase']:print(r['family'],r['seed'],r['gates'], 'outside-domain range',[min(x['outside_whole_mixture_alignment_domain'] for x in r['perturbations']),max(x['outside_whole_mixture_alignment_domain'] for x in r['perturbations'])],'kernel-energy-range',[min(x['learned_kernel_energy_ratio'] for x in r['perturbations']),max(x['learned_kernel_energy_ratio'] for x in r['perturbations'])])
