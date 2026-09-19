"""Independent development recordings for the four-epoch protocol; no field claim."""
import argparse
import json
from pathlib import Path
import numpy as np
from scipy.io import wavfile
from echosight.signals import generate_probe

def recording_protocol(folder, scenario='null', seed=420, receiver_count=12):
    root=Path(folder);rng=np.random.default_rng(seed);rate=48000;c=343.
    source=np.array([1.2,1.7,1.1]);receivers=rng.uniform([1.7,.6,.4],[3.,3.1,2.5],(receiver_count,3))
    probe,metadata=generate_probe({'period_s':.35,'high_hz':14000.})
    grid=np.arange(len(probe))/rate
    protocol={'schema_version':'1.0','protocol_id':'controlled-development','coordinate_frame_id':'survey-one',
        'intervention_description':'Move one large planar reflector0.2m toward the surveyed source, then restore it.',
        'controls':{'devices_and_source_stationary':True,'only_declared_intervention':True,'restoration_attempted':True,'differential_timing_std_s':3e-6},'epochs':[]}
    for epoch,label in enumerate(('A_before','B_first','B_repeat','A_return')):
        path=root/label;path.mkdir(parents=True,exist_ok=True)
        session={'schema_version':'1.0','session_id':label,'coordinate_frame_id':'survey-one',
            'source_position_m':source.tolist(),'source_position_std_m':.003,
            'sound_speed_m_s':343.,'sound_speed_std_m_s':.3,'source_clock_scale':1.,'source_clock_std_ppm':50.,
            'probe':metadata,'captures':[]}
        state_b=epoch in (1,2) or (scenario=='failed_return' and epoch==3)
        plane=4. if scenario in ('moved','failed_return') and state_b else 4.2
        image=source.copy();image[0]=2*plane-source[0]
        gain=.6 if scenario=='gain_only' and state_b else 1.
        for i,receiver in enumerate(receivers):
            direct=np.linalg.norm(receiver-source)/c;echo=np.linalg.norm(receiver-image)/c
            alpha=1+rng.uniform(-50,50)*1e-6;offset=rng.uniform(.04,.08)
            t=(np.arange(len(probe)+round(.2*rate))/rate-offset)/alpha
            samples=gain*(.5*np.interp(t-direct,grid,probe,left=0,right=0)+.3*np.interp(t-echo,grid,probe,left=0,right=0))
            samples+=rng.normal(0,1e-5,len(samples))
            name=path/f'phone-{i:02d}.wav';wavfile.write(name,rate,np.rint(samples*32767).astype('<i2'))
            session['captures'].append({'capture_id':f'view-{i:02d}','device_id':f'phone-{i:02d}',
                'receiver_pose_group_id':f'pose-{i:02d}','receiver_position_m':receiver.tolist(),
                'receiver_position_std_m':.003,'recording_path':str(name.resolve()),'provenance':'simulated','sample_rate_hz':rate})
        protocol['epochs'].append({'epoch':label,'session':session,'calibration_id':'cal-one',
            'source_configuration_id':'qualified-source-one','route_ids':{f'phone-{i:02d}':'raw-lossless-one' for i in range(receiver_count)}})
    return protocol


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--receivers',type=int,choices=(4,12),default=4)
    parser.add_argument('--scenario',choices=('null','moved','gain_only','failed_return'),default='moved')
    args=parser.parse_args()
    protocol=recording_protocol(args.output,args.scenario,receiver_count=args.receivers)
    path=args.output/'protocol.json';path.write_text(json.dumps(protocol,indent=2)+'\n')
    print(path)
