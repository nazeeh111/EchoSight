import copy,hashlib,io,json,struct,tempfile,zipfile
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import numpy as np
from tests.test_acquisition import capture_bytes
from echosight.acquisition import read_capture_package,read_float_wav
from echosight.storage import MAX_RECORDING_BYTES
out=[]
for name,mutation in [('host_time_one_second_jump',lambda m:m['continuity']['blocks'][1].update(host_time='2000000000')),('host_time_one_nanosecond_step',lambda m:m['continuity']['blocks'][1].update(host_time='1000000001')),('host_time_extreme_timebase',lambda m:m['host_timebase'].update(numer=4294967295,denom=1)),('entire_record_unsupported_bluetooth',lambda m:(m['route_initial'].update(input_port_type='BluetoothHFP'),m['route_final'].update(input_port_type='BluetoothHFP'))),('source_conflict_declaration',lambda m:m['source_declaration'].update(configuration_id='definitely-another-source',probe_id='different-probe',route_id='Bluetooth-speaker'))]:
 raw,_,_=capture_bytes(mutate=mutation);_,_,e=read_capture_package(raw,MAX_RECORDING_BYTES);out.append({'probe':name,**e['acquisition']})
# Span finite IEEE Float32 patterns, including signed zero/subnormals/max values.
rng=np.random.default_rng(20260921);bits=rng.integers(0,2**32,20000,dtype=np.uint32);x=bits.view(np.float32);x=x[np.isfinite(x)];x=np.concatenate([np.array([0.,-0.,np.nextafter(np.float32(0),np.float32(1)),np.finfo(np.float32).max],np.float32),x]);raw,audio,x=capture_bytes(x);decoded,rate,e=read_capture_package(raw,MAX_RECORDING_BYTES);assert decoded.astype('<f4').tobytes()==x.tobytes();out.append({'probe':'exact_float32_widening','finite_values_checked':len(x),'bit_preservation':True})
# High UInt64 values have exact integer-difference semantics, not JSON float loss.
raw,_,_=capture_bytes(mutate=lambda m:[b.update(host_time=str((2**64-100000)+i*62500)) for i,b in enumerate(m['continuity']['blocks'])]);_,_,e=read_capture_package(raw,MAX_RECORDING_BYTES);out.append({'probe':'uint64_above_javascript_integer_precision','frames_per_host_second':e['acquisition']['delivered_frames_per_host_second']})
Path('work/acquisition-review/probes.json').write_text(json.dumps(out,indent=2,allow_nan=False)+'\n');print([(x['probe'],x.get('processing_eligible'),x.get('delivered_frames_per_host_second')) for x in out])
