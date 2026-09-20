"""Conditional signed-response features for supplied material reference profiles.

No material labels, optical colors, absorption coefficients or calibrated noise
covariance are inferred here. Geometry and acquisition evidence remain unchanged.
"""
import hashlib
import json
import math
import re
import numpy as np
from .geometry import image_source, reflection_point
from .signals import DEFAULT_PROBE, generate_probe

FEATURE_VERSION = 'apparent-reflection-bands-v1'
BANDS_HZ = ((3000.,5000.), (5000.,8000.), (8000.,11000.), (11000.,13000.))
_HASH = re.compile(r'^[0-9a-f]{64}$')
_MAX_RESPONSE = 16000


class _Unavailable(ValueError):
    pass


def _number(value, low, high, code='malformed_feature_input'):
    if isinstance(value,bool) or not isinstance(value,(int,float,np.integer,np.floating)) or not math.isfinite(value) or not low <= value <= high:
        raise _Unavailable(code)
    return float(value)


def _vector(value, code='nonfinite_geometry'):
    if not isinstance(value,(list,tuple)) or len(value)!=3:
        raise _Unavailable(code)
    return np.array([_number(x,-1000,1000,code) for x in value])


def _probe(probe):
    if not isinstance(probe,dict):raise ValueError('probe must be an object')
    try:
        if len(json.dumps(probe,allow_nan=False).encode())>65536:raise ValueError('probe exceeds feature limit')
    except (TypeError,OverflowError) as exc:raise ValueError('probe must contain finite JSON') from exc
    # Reuse the authoritative generator's bounded parameter validation.
    _,canonical=generate_probe(probe)
    for key in ('sample_count','pilot_start_samples','waveform_sha256','kind','timing_unit'):
        if key in probe and probe[key]!=canonical[key]:raise ValueError('probe metadata disagrees with generated waveform')
    values={key:(int(canonical[key]) if key in ('sample_rate_hz','repetitions') else float(canonical[key])) for key in DEFAULT_PROBE}
    values.update(kind=canonical['kind'],timing_unit=canonical['timing_unit'],waveform_sha256=canonical['waveform_sha256'])
    fingerprint=hashlib.sha256(json.dumps(values,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    return canonical,fingerprint


def probe_fingerprint(probe):
    """Bind the validated emitted waveform and source-buffer frequency convention.

    Canonical defaults/numeric spellings agree. Physical route identity is a
    separate supplied profile condition; a probe hash does not qualify a device.
    """
    return _probe(probe)[1]


def _unknown(row, code):
    return {**row,'status':'unknown','diagnostic_codes':[code]}


def _spectrum(values, fs, start, delay, halfwidth):
    center=round((delay-start)*fs);radius=round(halfwidth*fs)
    if center-radius<0 or center+radius>=len(values):raise _Unavailable('window_truncated')
    samples=values[center-radius:center+radius+1];window=np.hanning(len(samples))
    transform=np.fft.rfft(samples*window);frequencies=np.fft.rfftfreq(len(samples),1/fs)
    powers=[]
    for low,high in BANDS_HZ:
        selected=(frequencies>=low)&(frequencies<high)
        if np.count_nonzero(selected)<2:raise _Unavailable('insufficient_band_bins')
        power=float(np.sum(abs(transform[selected])**2))
        if not math.isfinite(power) or power<=0:raise _Unavailable('weak_band_energy_proxy')
        powers.append(power)
    return np.array(powers),float(np.sqrt(np.sum(window*window)))


def _geometry(surface, acquisition, observation, capture, support):
    source=_vector(acquisition.get('source_position_m'));receiver=_vector(observation.get('receiver_position_m'))
    if not np.allclose(receiver,_vector(capture.get('receiver_position_m')),rtol=0,atol=1e-8):
        raise _Unavailable('support_binding_invalid')
    normal=_vector(surface.get('normal'));offset=_number(surface.get('offset_m'),-1000,1000,'nonfinite_geometry')
    if not np.isclose(np.linalg.norm(normal),1.,rtol=0,atol=1e-6):raise _Unavailable('unsupported_reflection_geometry')
    image=image_source(source,normal,offset)
    if not np.allclose(_vector(surface.get('image_source_m')),image,rtol=0,atol=1e-7):raise _Unavailable('support_binding_invalid')
    point=reflection_point(source,receiver,normal,offset)
    if point is None:raise _Unavailable('unsupported_reflection_geometry')
    if 'reflection_point_m' in support and not np.allclose(_vector(support['reflection_point_m']),point,rtol=0,atol=1e-6):
        raise _Unavailable('support_binding_invalid')
    for key,value in (('source_position_m',source),('receiver_position_m',receiver)):
        if key in support and not np.allclose(_vector(support[key]),value,rtol=0,atol=1e-8):raise _Unavailable('support_binding_invalid')
    direct=float(np.linalg.norm(receiver-source));reflected=float(np.linalg.norm(receiver-image))
    if direct<.05 or reflected<=direct or not np.isfinite(reflected):raise _Unavailable('unsupported_reflection_geometry')
    if 'predicted_delay_s' in support:
        speed=acquisition.get('effective_speed_m_s')
        if speed is None:
            speed=_number(acquisition.get('sound_speed_m_s',343.),250,450)/_number(acquisition.get('source_clock_scale',1.),.98,1.02)
        speed=_number(speed,250,460)
        predicted=_number(support['predicted_delay_s'],0,.15,'support_binding_invalid')
        if abs(predicted-(reflected-direct)/speed)>1e-8:raise _Unavailable('support_binding_invalid')
    incoming=(source-point)/np.linalg.norm(source-point)
    incidence=float(np.degrees(np.arccos(np.clip(abs(normal@incoming),0,1))))
    return dict(incidence_angle_deg=incidence,direct_length_m=direct,reflected_length_m=reflected,
        source_direct_bearing=(receiver-source).tolist(),source_reflection_bearing=(point-source).tolist(),
        receiver_direct_bearing=(source-receiver).tolist(),receiver_reflection_bearing=(point-receiver).tolist())


def _one(row, support, surface, acquisition, observation, capture, probe, fingerprint):
    if observation.get('status')!='ok':raise _Unavailable('response_unavailable')
    response=observation.get('response');quality=observation.get('quality')
    if not isinstance(response,dict) or not isinstance(quality,dict):raise _Unavailable('response_unavailable')
    candidates=observation.get('candidates')
    if not isinstance(candidates,list) or not 1<=len(candidates)<=18 or any(not isinstance(p,dict) for p in candidates):raise _Unavailable('candidate_catalog_invalid')
    codes=[d.get('code') for d in observation.get('diagnostics',[]) if isinstance(d,dict)]
    if 'candidate_budget' in codes:raise _Unavailable('candidate_catalog_truncated')
    if 'direct_reference_ambiguous' in codes or observation.get('direct_reference_alternatives_s'):raise _Unavailable('direct_reference_ambiguous')
    candidate_ids=[p.get('candidate_id') for p in candidates]
    if len(set(candidate_ids))!=len(candidate_ids):raise _Unavailable('support_binding_invalid')
    matched=[p for p in candidates if p.get('candidate_id')==row['candidate_id']]
    if len(matched)!=1:raise _Unavailable('support_binding_invalid')
    candidate=matched[0]
    if candidate.get('merged',False):raise _Unavailable('merged_candidate')
    delay=_number(candidate.get('delay_s'),0,.15,'support_binding_invalid')
    declared=_number(support.get('observed_delay_s'),0,.15,'support_binding_invalid')
    if abs(delay-declared)>1e-10:raise _Unavailable('support_binding_invalid')
    fs=_number(response.get('sample_rate_hz'),16000,96000,'frequency_clock_unsupported')
    if fs!=probe['sample_rate_hz'] or response.get('delay_unit')!='source_buffer_seconds':raise _Unavailable('frequency_clock_unsupported')
    band=quality.get('usable_band_hz')
    if not isinstance(band,list) or len(band)!=2 or band!=[probe['low_hz'],probe['high_hz']]:raise _Unavailable('bands_outside_supported_probe_interior')
    if BANDS_HZ[0][0]<probe['low_hz']+1000 or BANDS_HZ[-1][1]>probe['high_hz']-1000:raise _Unavailable('bands_outside_supported_probe_interior')
    values=response.get('values')
    if not isinstance(values,list) or not 3<=len(values)<=_MAX_RESPONSE:raise _Unavailable('response_unavailable')
    values=np.array([_number(x,-1000,1000,'malformed_response') for x in values])
    start=_number(response.get('start_delay_s'),-.02,.0,'frequency_clock_unsupported')
    noise=_number(quality.get('noise_response_amplitude'),0,1000,'noise_proxy_unavailable')
    _number(quality.get('direct_response_amplitude'),1e-12,1000,'weak_direct')
    delays=[_number(p.get('delay_s'),0,.15,'candidate_catalog_invalid') for p in candidates]
    nearest=min([delay]+[abs(delay-t) for p,t in zip(candidates,delays) if p['candidate_id']!=row['candidate_id']])
    if nearest<=.0015 or min(delays)<=.0015:raise _Unavailable('overlapping_detected_paths')
    geometry=_geometry(surface,acquisition,observation,capture,support)
    direct,scale=_spectrum(values,fs,start,0.,.0005);echo,_=_spectrum(values,fs,start,delay,.0005)
    wide_direct,_=_spectrum(values,fs,start,0.,.00075);wide_echo,_=_spectrum(values,fs,start,delay,.00075)
    if min(float(np.sqrt(direct).min()),float(np.sqrt(echo).min()))<12*noise*scale:raise _Unavailable('weak_band_energy_proxy')
    ratios=10*np.log10(echo/direct);wide=10*np.log10(wide_echo/wide_direct)
    change=float(max(abs(ratios-wide)))
    if not math.isfinite(change) or change>1.:raise _Unavailable('window_sensitive_spectrum')
    correction=20*np.log10(geometry['reflected_length_m']/geometry['direct_length_m'])
    feature=ratios+correction
    if not np.isfinite(feature).all():raise _Unavailable('malformed_feature_input')
    for key in ('source_direct_bearing','source_reflection_bearing','receiver_direct_bearing','receiver_reflection_bearing'):
        vector=np.array(geometry[key]);geometry[key]=(vector/np.linalg.norm(vector)).tolist()
    return dict(row,**geometry,status='ok',diagnostic_codes=[],feature_version=FEATURE_VERSION,probe_sha256=fingerprint,
        feature_db=feature.tolist(),bands_hz=[list(b) for b in BANDS_HZ],uncorrected_ratio_db=ratios.tolist(),
        window_change_max_db=change,window_duration_s=(2*round(.0005*fs)+1)/fs,
        noise_guard_semantics='Repeat-difference amplitude proxy; not calibrated spectral SNR or feature covariance.',
        semantics='Apparent signed matched-response reflection gains under spherical pressure spreading; not absorption coefficients or material identification.')


def extract_surface_features(result, surface, cancel=None):
    """Preserve every supplied support, including unsupported/unknown records.

    Cancellation retracts all feature claims for this surface. Returned gains need
    a compatible supplied profile and acquisition domain before material matching.
    """
    if not isinstance(result,dict) or not isinstance(surface,dict):raise ValueError('result and surface must be objects')
    supports=surface.get('support',[])
    if not isinstance(supports,list) or len(supports)>64:raise ValueError('surface support must be a bounded list')
    rows=[]
    for support in supports:
        s=support if isinstance(support,dict) else {}
        rows.append(dict(capture_id=s.get('capture_id'),candidate_id=s.get('candidate_id'),recording_sha256=None,waveform_sha256=None))
    def unavailable(code):return [_unknown(row,code) for row in rows]
    if cancel and cancel():return unavailable('cancelled')
    if result.get('status')=='cancelled':return unavailable('cancelled')
    if result.get('status') not in ('ok','partial') or surface.get('model_status')!='conditional_first_order_hypothesis':return unavailable('unsupported_geometry_status')
    acquisition=result.get('acquisition');observations=result.get('observations');surfaces=result.get('surfaces')
    if not isinstance(acquisition,dict) or not isinstance(observations,list) or len(observations)>32 or not isinstance(surfaces,list):return unavailable('acquisition_unavailable')
    if not isinstance(acquisition.get('coordinate_frame_id'),str) or not 1<=len(acquisition['coordinate_frame_id'])<=160:return unavailable('coordinate_frame_unavailable')
    declared=[s for s in surfaces if isinstance(s,dict) and s.get('surface_id')==surface.get('surface_id')]
    if len(declared)!=1 or declared[0]!=surface:return unavailable('support_binding_invalid')
    captures=acquisition.get('captures')
    if not isinstance(captures,list) or len(captures)>32:return unavailable('acquisition_unavailable')
    try:probe,fingerprint=_probe(acquisition.get('probe'))
    except (ValueError,TypeError,OverflowError):return unavailable('unsupported_probe')
    output=[];seen=set()
    for row,support in zip(rows,supports):
        if cancel and cancel():return unavailable('cancelled')
        try:
            if not isinstance(support,dict) or not isinstance(row['capture_id'],str) or not isinstance(row['candidate_id'],str):raise _Unavailable('support_binding_invalid')
            identity=(row['capture_id'],row['candidate_id'])
            if identity in seen:raise _Unavailable('support_binding_invalid')
            seen.add(identity)
            obs=[o for o in observations if isinstance(o,dict) and o.get('capture_id')==row['capture_id']]
            cap=[c for c in captures if isinstance(c,dict) and c.get('capture_id')==row['capture_id']]
            if len(obs)!=1 or len(cap)!=1:raise _Unavailable('support_binding_invalid')
            for key in ('recording_sha256','waveform_sha256'):
                value=obs[0].get(key)
                if not isinstance(value,str) or not _HASH.fullmatch(value):raise _Unavailable('recording_identity_unavailable')
                row[key]=value
            if cap[0].get('sha256') not in (None,row['recording_sha256']):raise _Unavailable('support_binding_invalid')
            output.append(_one(row,support,surface,acquisition,obs[0],cap[0],probe,fingerprint))
        except _Unavailable as exc:output.append(_unknown(row,str(exc)))
        except (TypeError,ValueError,KeyError,OverflowError,IndexError):output.append(_unknown(row,'malformed_feature_input'))
    if cancel and cancel():return unavailable('cancelled')
    return output
