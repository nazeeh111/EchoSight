import sys,io,json,zipfile,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import numpy as np
from tests.test_acquisition import capture_bytes
from echosight.acquisition import read_capture_package
from echosight.storage import MAX_RECORDING_BYTES
rows=[]
def trial(name,expected,host_scale=1.,tick_numer=1,tick_denom=1,host_jump_index=None,host_jump=0,block_frames=480,blocks_count=40):
 def change(m):
  m['host_timebase']={'numer':tick_numer,'denom':tick_denom};m['continuity']['blocks']=[]
  for i in range(blocks_count):
   first=i*block_frames;seconds=first/48000*host_scale
   if host_jump_index is not None and i>=host_jump_index:seconds+=host_jump
   ticks=round(seconds/(tick_numer/tick_denom/1e9))
   m['continuity']['blocks'].append(dict(sequence=i,first_frame=first,frame_count=block_frames,sample_time_valid=True,sample_time=str(first-100),host_time_valid=True,host_time=str(10000000000000000+ticks)))
 raw,_,_=capture_bytes(np.zeros(blocks_count*block_frames,np.float32),change);_,_,e=read_capture_package(raw,MAX_RECORDING_BYTES);a=e['acquisition'];assert a['processing_eligible']==expected,(name,a)
 rows.append(dict(name=name,expected_eligible=expected,actual_eligible=a['processing_eligible'],reasons=a['rejection_reasons'],check=a.get('host_sample_time_check')))
trial('consistent_48k',True)
trial('plus_5000ppm_host_scale',True,host_scale=1.005)
trial('minus_5000ppm_host_scale',True,host_scale=.995)
trial('cumulative_130us_per10ms_below_adjacent_allowance',False,host_scale=1.013)
trial('one_second_gap',False,host_jump_index=20,host_jump=1)
trial('host_progression_one_nanosecond_per_block',False,host_scale=1e-7)
trial('unresolvable_tick_timebase',False,tick_numer=4294967295)
trial('fractional_mach_tick_125_over3',True,tick_numer=125,tick_denom=3)
trial('subthreshold_step_is_not_guaranteed_detected',True,host_jump_index=20,host_jump=8e-5)
Path('work/acquisition-review/recheck.json').write_text(json.dumps({'passed':True,'cases':rows},indent=2)+'\n');print([(r['name'],r['actual_eligible']) for r in rows])
