"""Lossless delivered Float32 and hash-bound native acquisition observations.

Metadata is a recorder declaration, not authentication or hardware validation.
"""
from __future__ import annotations
import hashlib
import io
import json
import math
import re
import struct
import zipfile
import zlib
import numpy as np

MAX_MANIFEST_BYTES=1024*1024
MAX_BLOCKS=16384


def read_float_wav(raw):
    """Return Float32 widened exactly to Float64, or None for other WAV codecs."""
    if len(raw)<12 or raw[:4]!=b'RIFF' or raw[8:12]!=b'WAVE':return None
    position=12;fmt=None;data=None;chunks=0
    while position+8<=len(raw):
        name,size=struct.unpack_from('<4sI',raw,position);position+=8;chunks+=1
        if chunks>128:raise ValueError('too many WAV chunks')
        if size>len(raw)-position:raise ValueError('truncated WAV chunk')
        payload=raw[position:position+size];position+=size+(size%2)
        if name==b'fmt ':
            if fmt is not None:raise ValueError('duplicate WAV format')
            fmt=payload
            if len(fmt)<16:raise ValueError('short WAV format')
            if struct.unpack_from('<H',fmt)[0]!=3:return None
        if name==b'data':
            if data is not None:raise ValueError('duplicate WAV data')
            data=payload
    if fmt is None or struct.unpack_from('<H',fmt)[0]!=3:return None
    if struct.unpack_from('<I',raw,4)[0]+8!=len(raw) or position!=len(raw):raise ValueError('inconsistent Float32 RIFF length')
    codec,channels,rate,byte_rate,align,bits=struct.unpack_from('<HHIIHH',fmt)
    if channels!=1 or bits!=32 or align!=4 or byte_rate!=rate*4:raise ValueError('Float WAV must be mono IEEE Float32 without conversion')
    if data is None or len(data)%4 or not 8000<=rate<=192000 or not 1<=len(data)//4<=120*rate:raise ValueError('invalid Float32 rate, frames or duration')
    samples=np.frombuffer(data,dtype='<f4')
    if not np.isfinite(samples).all():raise ValueError('nonfinite Float32 samples')
    return samples.astype(np.float64),rate


def _integer(value,name,low,high):
    if isinstance(value,bool) or not isinstance(value,int) or not low<=value<=high:raise ValueError(name+' outside integer bounds')
    return value


def _text(value,name,limit=160):
    if not isinstance(value,str) or not 1<=len(value)<=limit:raise ValueError(name+' must be a bounded nonempty string')
    return value


def _ticks(value,name,signed=False):
    pattern=r'-?[0-9]{1,19}' if signed else r'[0-9]{1,20}'
    if not isinstance(value,str) or not re.fullmatch(pattern,value):raise ValueError(name+' must be a decimal integer string')
    integer=int(value)
    if not (-(2**63) if signed else 0)<=integer<=(2**63-1 if signed else 2**64-1):raise ValueError(name+' out of bounds')
    return integer


def validate_manifest(manifest,audio,samples,rate):
    if not isinstance(manifest,dict):raise ValueError('capture manifest must be an object')
    # This also rejects nonfinite JSON in optional metadata before storing a summary.
    try:json.dumps(manifest,allow_nan=False)
    except (ValueError,TypeError,RecursionError) as exc:raise ValueError('manifest must contain finite bounded JSON') from exc
    if manifest.get('schema_version')!='1.0' or manifest.get('format')!='echosight_capture':raise ValueError('unsupported capture manifest')
    cid=_text(manifest.get('capture_id'),'capture_id',80)
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}',cid):raise ValueError('invalid manifest capture ID')
    if manifest.get('recording_sha256')!=hashlib.sha256(audio).hexdigest():raise ValueError('recording hash differs from manifest')
    if manifest.get('sample_encoding')!='ieee_float32_le':raise ValueError('unsupported delivered sample encoding')
    if _integer(manifest.get('sample_rate_hz'),'sample rate',8000,192000)!=rate:raise ValueError('manifest rate differs from WAV')
    if _integer(manifest.get('channel_count'),'channels',1,1)!=1 or _integer(manifest.get('frame_count'),'frames',1,rate*120)!=len(samples):raise ValueError('manifest frame count differs from WAV')
    if manifest.get('acquisition_layer')!='ios_audioengine_delivered_buffers':raise ValueError('unsupported acquisition layer')
    for parent,keys in [('recorder',('name','version')),('device',('model','os_version')),('source_declaration',('configuration_id','probe_id','route_id'))]:
        obj=manifest.get(parent)
        if not isinstance(obj,dict):raise ValueError(parent+' must be an object')
        for key in keys:_text(obj.get(key),parent+'.'+key)
    session=manifest.get('session');initial=manifest.get('route_initial');final=manifest.get('route_final')
    if any(not isinstance(x,dict) for x in (session,initial,final)):raise ValueError('session and route snapshots required')
    for route in (initial,final):
        for key in ('input_port_type','input_port_name'):_text(route.get(key),key)
        _integer(route.get('input_channel_count'),'route channels',1,64)
        _integer(route.get('input_sample_rate_hz'),'route sample rate',8000,192000)
    _text(session.get('category'),'session category');_text(session.get('mode'),'session mode')
    for key in ('preferred_sample_rate_hz','activated_sample_rate_hz'):
        value=session.get(key)
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or not 8000<=value<=192000:raise ValueError('invalid session sample rate')
    base=manifest.get('host_timebase')
    if not isinstance(base,dict):raise ValueError('host timebase required')
    for key in ('numer','denom'):_integer(base.get(key),'timebase '+key,1,2**32-1)
    continuity=manifest.get('continuity')
    if not isinstance(continuity,dict) or continuity.get('status') not in ('complete','interrupted','unverified'):raise ValueError('invalid continuity declaration')
    reasons=continuity.get('reasons');blocks=continuity.get('blocks')
    if not isinstance(reasons,list) or len(reasons)>256:raise ValueError('invalid continuity reasons')
    for reason in reasons:_text(reason,'continuity reason',512)
    if not isinstance(blocks,list) or not 1<=len(blocks)<=MAX_BLOCKS:raise ValueError('invalid or excessive acquisition block count')
    rejection=[];cursor=0;previous=None;first_timed=None;host_values=[];frame_values=[]
    tick_seconds=base['numer']/base['denom']/1e9
    max_host_sample_error_s=0.
    if tick_seconds>.1/rate:rejection.append('host_timer_resolution_unqualified')
    for index,block in enumerate(blocks):
        if not isinstance(block,dict):raise ValueError('block must be an object')
        if _integer(block.get('sequence'),'sequence',0,MAX_BLOCKS-1)!=index or _integer(block.get('first_frame'),'first_frame',0,len(samples))!=cursor:raise ValueError('manifest blocks do not cover stored frames contiguously')
        count=_integer(block.get('frame_count'),'block frames',1,len(samples));cursor+=count
        if cursor>len(samples):raise ValueError('block frames exceed recording')
        times={}
        for name,signed in [('sample_time',True),('host_time',False)]:
            valid=block.get(name+'_valid')
            if not isinstance(valid,bool):raise ValueError('timestamp validity must be boolean')
            if valid:times[name]=_ticks(block.get(name),name,signed)
            else:
                if block.get(name) is not None:raise ValueError('invalid timestamp must be null')
                times[name]=None;rejection.append('timestamp_invalid')
        if previous is not None:
            if times['sample_time'] is not None and previous['sample_time'] is not None and times['sample_time']!=previous['sample_time']+previous['frame_count']:rejection.append('native_sample_time_gap_or_overlap')
            if times['host_time'] is not None and previous['host_time'] is not None and times['host_time']<=previous['host_time']:rejection.append('host_time_not_increasing')
        if times['host_time'] is not None and times['sample_time'] is not None:
            for origin in (previous,first_timed):
                if origin is None or origin['host_time'] is None or origin['sample_time'] is None:continue
                sample_elapsed=(times['sample_time']-origin['sample_time'])/rate
                host_elapsed=(times['host_time']-origin['host_time'])*tick_seconds
                error=abs(host_elapsed-sample_elapsed)
                max_host_sample_error_s=max(max_host_sample_error_s,error)
                # Broad engineering admission bound, not a calibrated jitter model.
                allowance=.01*max(0.,sample_elapsed)+2/rate+2*tick_seconds
                if sample_elapsed<=0 or host_elapsed<=0 or error>allowance:rejection.append('host_sample_time_inconsistent')
            if first_timed is None:first_timed=dict(times)
        if times['host_time'] is not None:host_values.append(times['host_time']);frame_values.append(block['first_frame'])
        previous=dict(times,frame_count=count)
    if cursor!=len(samples):raise ValueError('manifest blocks do not cover complete recording')
    events=manifest.get('events')
    if not isinstance(events,list) or len(events)>256:raise ValueError('invalid acquisition event list')
    for event in events:
        if not isinstance(event,dict):raise ValueError('event must be an object')
        kind=_text(event.get('type'),'event type',80);_integer(event.get('at_frame'),'event frame',0,len(samples))
        _text(event.get('detail'),'event detail',512)
        if kind not in ('user_stop','duration_limit'):rejection.append('acquisition_event:'+kind)
    if continuity['status']!='complete' or reasons:rejection.append('recorder_continuity_not_complete')
    if initial!=final:rejection.append('route_changed')
    if session['mode'] not in ('measurement','AVAudioSessionModeMeasurement') or session['category'] not in ('record','AVAudioSessionCategoryRecord'):rejection.append('measurement_route_unqualified')
    if session['activated_sample_rate_hz']!=rate or any(r['input_sample_rate_hz']!=rate or r['input_channel_count']!=1 for r in (initial,final)):rejection.append('delivered_format_differs_from_activated_route')
    summary={'capture_id':cid,'recording_sha256':manifest['recording_sha256'],'acquisition_layer':manifest['acquisition_layer'],
        'recorder':manifest['recorder'],'device':manifest['device'],'source_declaration':manifest['source_declaration'],
        'session':session,'route_initial':initial,'route_final':final,'block_count':len(blocks),'frame_count':len(samples),
        'declared_continuity_status':continuity['status'],'host_sample_time_check':{'max_discrepancy_s':max_host_sample_error_s,'allowance':'1% of sample interval plus two sample periods plus two host ticks; adjacent and first-to-current blocks','semantics':'Engineering admission bound, not physical clock calibration or guaranteed sub-buffer discontinuity detection'},'events':events,'rejection_reasons':sorted(set(rejection)),
        'processing_eligible':not rejection,'physical_validation':False,
        'clock_semantics':'Native delivered-frame timestamps and unsynchronized host ticks; not source-buffer or calibrated physical time.',
        'processing_semantics':'No conversion added by this importer; OS/device processing and actual recorder behavior await hardware qualification.'}
    if len(host_values)>=2 and host_values[-1]>host_values[0]:
        elapsed=(host_values[-1]-host_values[0])*base['numer']/base['denom']/1e9
        summary['delivered_frames_per_host_second']=(frame_values[-1]-frame_values[0])/elapsed
    return summary


def read_capture_package(raw,max_bytes):
    """None means an unrelated ZIP; known capture packages fail closed."""
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            infos=archive.infolist()
            if not any(i.filename=='manifest.json' for i in infos):return None
            if len(infos)!=2 or {i.filename for i in infos}!={'manifest.json','recording.wav'}:raise ValueError('capture ZIP must contain exactly manifest.json and recording.wav')
            if any(i.flag_bits&1 or i.compress_type not in (zipfile.ZIP_STORED,zipfile.ZIP_DEFLATED) for i in infos):raise ValueError('unsupported capture ZIP encoding')
            if sum(i.file_size for i in infos)>max_bytes or archive.getinfo('manifest.json').file_size>MAX_MANIFEST_BYTES:raise ValueError('capture package exceeds expanded resource limit')
            manifest_bytes=archive.read('manifest.json');audio=archive.read('recording.wav')
    except (zipfile.BadZipFile,RuntimeError,NotImplementedError,zlib.error,EOFError) as exc:raise ValueError('invalid capture ZIP') from exc
    try:manifest=json.loads(manifest_bytes)
    except (ValueError,UnicodeError,RecursionError) as exc:raise ValueError('invalid capture manifest JSON') from exc
    decoded=read_float_wav(audio)
    if decoded is None:raise ValueError('capture package requires IEEE Float32 WAV')
    samples,rate=decoded;summary=validate_manifest(manifest,audio,samples,rate)
    summary['manifest_sha256']=hashlib.sha256(manifest_bytes).hexdigest()
    return samples,rate,{'format':'echosight_capture_zip','acquisition':summary,
        'diagnostics':['delivered_audio_not_raw_adc','phone_export_not_hardware_validated']+summary['rejection_reasons']}
