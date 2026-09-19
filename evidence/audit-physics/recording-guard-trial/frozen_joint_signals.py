"""Bounded repeated-probe processing. All recovered delays use source-buffer seconds."""
from __future__ import annotations
import hashlib
import math
import numpy as np
from scipy.signal import chirp, correlate, find_peaks
from scipy.signal.windows import tukey

DEFAULT_PROBE = dict(sample_rate_hz=48000, duration_s=.04, low_hz=2000., high_hz=15000.,
                     repetitions=7, period_s=.22, lead_s=.1, tail_s=.18,
                     max_echo_delay_s=.08)


def generate_probe(config=None):
    """Render one buffer; caller must never schedule repetitions as separate play calls."""
    config = {} if config is None else dict(config)
    p = dict(DEFAULT_PROBE)
    for key in DEFAULT_PROBE:
        if key in config:
            p[key] = config[key]
    if any(not isinstance(v, (int, float)) or not np.isfinite(v) for v in p.values()):
        raise ValueError('probe values must be finite numbers')
    fs = p['sample_rate_hz']
    count = p['repetitions']
    if fs != int(fs) or not 16000 <= fs <= 96000 or count != int(count) or not 4 <= count <= 16:
        raise ValueError('sample rate or repetitions outside limits')
    if not .015 <= p['duration_s'] <= .15 or not 100 <= p['low_hz'] < p['high_hz'] <= fs*.45:
        raise ValueError('invalid probe duration or band')
    if not .01 <= p['max_echo_delay_s'] <= .15 or not .1 <= p['period_s'] <= 1:
        raise ValueError('invalid echo window or period')
    if p['period_s'] < p['duration_s'] + p['max_echo_delay_s'] + .02:
        raise ValueError('probe repetitions overlap analysis window')
    if not 0 <= p['lead_s'] <= 1 or not p['max_echo_delay_s'] <= p['tail_s'] <= 1:
        raise ValueError('invalid lead/tail')
    fs, count = int(fs), int(count)
    p.update(sample_rate_hz=fs, repetitions=count)
    length = round(p['duration_s']*fs)
    t = np.arange(length)/fs
    pulse = .7*chirp(t,p['low_hz'],p['duration_s'],p['high_hz'],method='linear')*tukey(length,.25)
    starts = [round((p['lead_s']+i*p['period_s'])*fs) for i in range(count)]
    out = np.zeros(starts[-1]+length+round(p['tail_s']*fs))
    for start in starts:
        out[start:start+length] = pulse
    p.update(schema_version='1.0',kind='repeated_linear_chirp',pilot_start_samples=starts,
             sample_count=len(out), waveform_sha256=hashlib.sha256(out.astype('<f8').tobytes()).hexdigest(),
             timing_unit='source_buffer_seconds')
    return out, p



def generate_playback(config=None, channel='mono'):
    """Route the canonical probe to a mono stream or one explicit stereo channel.

    A software channel is not proof that only one physical driver radiates.
    """
    if channel not in ('mono','left','right'):
        raise ValueError('playback channel must be mono, left or right')
    samples,metadata=generate_probe(config)
    if channel != 'mono':
        stereo=np.zeros((len(samples),2))
        stereo[:,0 if channel=='left' else 1]=samples
        samples=stereo
    metadata['playback']=dict(channel=channel,channels=1 if channel=='mono' else 2,
                              single_continuous_buffer=True,physical_driver_calibrated=False)
    return samples,metadata


def _peak_time(y, index):
    """Quadratic localization of an isolated correlation-envelope maximum."""
    if index <= 0 or index >= len(y)-1:
        return float(index)
    a,b,c = y[index-1:index+2]
    den = a-2*b+c
    return float(index + np.clip(.5*(a-c)/den,-.5,.5)) if abs(den)>1e-20 else float(index)


def process_recording(samples, sample_rate_hz, probe, capture_id, sound_speed_m_s=343., cancel=None, estimator="matched_filter"):
    """Detect repeated direct arrivals, correct relative clock, extract unlabeled echoes.

    An earliest repeatable arrival is a *direct-path assumption*. A blocked direct
    path can violate it; geometry residuals and hardware qualification remain needed.
    """
    if estimator not in ('matched_filter','joint_kernel'):
        raise ValueError('unsupported response estimator')
    result = dict(capture_id=capture_id,status='rejected',estimator=estimator,diagnostics=[],clock={},candidates=[])
    def reject(code,message):
        result['diagnostics'].append(dict(code=code,message=message))
        return result
    if cancel and cancel():
        return reject('cancelled','Processing cancelled.')
    y = np.asarray(samples,dtype=float)
    if y.ndim != 1 or not np.all(np.isfinite(y)):
        raise ValueError('recording must be finite mono samples')
    if not isinstance(sample_rate_hz,(int,float)) or not np.isfinite(sample_rate_hz) or sample_rate_hz != int(sample_rate_hz) or not 16000 <= sample_rate_hz <= 96000:
        raise ValueError('unsupported recording sample rate')
    fs = int(sample_rate_hz)
    if len(y)>fs*30:
        raise ValueError('recording exceeds 30 second processing limit')
    x,p = generate_probe(probe)
    if p['high_hz'] > .45*fs:
        return reject('receiver_band_unsupported','Delivered recording rate cannot support the full emitted probe band; regenerate a compatible probe.')
    for field in ('sample_count','pilot_start_samples'):
        if field in probe and probe[field] != p[field]:
            raise ValueError(f'probe {field} does not match rendered configuration')
    if probe.get('kind',p['kind']) != p['kind']:
        raise ValueError('unsupported probe kind')
    if probe.get('waveform_sha256',p['waveform_sha256']) != p['waveform_sha256']:
        raise ValueError('probe waveform does not match configuration')
    if len(y)<fs*.5 or np.sqrt(np.mean(y*y))<1e-6:
        return reject('insufficient_signal','Recording is too short or silent.')
    clipped = float(np.mean(np.abs(y)>=.999))
    if clipped>.0001:
        return reject('clipped','Recording clips; reduce playback or recording gain.')
    # Resample the known pulse to receiver nominal rate only for initial acquisition.
    src_fs=p['sample_rate_hz']
    pulse=x[p['pilot_start_samples'][0]:p['pilot_start_samples'][0]+round(p['duration_s']*src_fs)]
    template=np.interp(np.arange(round(p['duration_s']*fs))/fs,np.arange(len(pulse))/src_fs,pulse)
    corr=correlate(y,template,mode='valid',method='fft')
    envelope=np.abs(corr)
    floor=float(np.median(envelope))
    spread=float(np.median(np.abs(envelope-floor)))
    threshold=max(float(envelope.max())*.10, floor+15*max(spread,1e-12))
    peaks,_=find_peaks(envelope,height=threshold,distance=max(1,round(fs*.0003)))
    if len(peaks)<p['repetitions']:
        return reject('pilots_not_found','Insufficient repeated pilot arrivals above noise.')
    # Earliest complete train above a noise-and-relative-amplitude threshold.
    # A bounded 0.6% slope search accommodates independent phone sample clocks.
    starts=np.array(p['pilot_start_samples'],dtype=float)/src_fs
    train=None
    search_span=.006
    for first in peaks[:256]:
        times=[_peak_time(envelope,int(first))/fs]
        chosen=[int(first)]
        for i in range(1,len(starts)):
            predicted=times[0]+starts[i]-starts[0]
            radius=max(.002,search_span*(starts[i]-starts[0]))
            options=peaks[np.abs(peaks/fs-predicted)<radius]
            if not len(options):
                break
            # Earliest significant path, not the strongest echo in the window.
            pick=int(options[0]); chosen.append(pick)
            times.append(_peak_time(envelope,pick)/fs)
        if len(times)==len(starts):
            train=np.asarray(times)
            break
    if train is None:
        return reject('pilots_not_found','No complete indexed pilot train; recording may be interrupted.')
    design=np.column_stack([starts,np.ones(len(starts))])
    alpha,intercept=np.linalg.lstsq(design,train,rcond=None)[0]
    residual=train-design@np.array([alpha,intercept])
    acquisition_refined=False
    # A rate-mismatched chirp can split one correlation maximum into sidelobes.
    # Only retry a failed affine fit, using its bounded coarse rate to match
    # the pulse duration. The corrected train must pass the same residual gate.
    if np.max(np.abs(residual))>max(2/fs,.00010) and abs(alpha-1)<=.005:
        stretched=np.interp(np.arange(round(p['duration_s']*fs*alpha))/(fs*alpha),
                            np.arange(len(pulse))/src_fs,pulse)
        refined_corr=correlate(y,stretched,mode='valid',method='fft')
        refined_envelope=np.abs(refined_corr)
        refined_floor=float(np.median(refined_envelope))
        refined_spread=float(np.median(np.abs(refined_envelope-refined_floor)))
        refined_threshold=max(float(refined_envelope.max())*.10,
                              refined_floor+15*max(refined_spread,1e-12))
        refined_peaks,_=find_peaks(refined_envelope,height=refined_threshold,
                                  distance=max(1,round(fs*.0003)))
        refined_train=[]
        for expected in alpha*starts+intercept:
            choices=refined_peaks[np.abs(refined_peaks/fs-expected)<.001]
            if not len(choices):
                break
            # Coarse fit is within the local window; choose its closest arrival.
            chosen=int(choices[np.argmin(np.abs(choices/fs-expected))])
            refined_train.append(_peak_time(refined_envelope,chosen)/fs)
        if len(refined_train)==len(starts):
            next_train=np.asarray(refined_train)
            next_alpha,next_intercept=np.linalg.lstsq(design,next_train,rcond=None)[0]
            next_residual=next_train-design@np.array([next_alpha,next_intercept])
            if np.max(np.abs(next_residual))<np.max(np.abs(residual)):
                train=next_train;alpha=next_alpha;intercept=next_intercept;residual=next_residual
                template=stretched;corr=refined_corr;envelope=refined_envelope
                floor=refined_floor;spread=refined_spread;peaks=refined_peaks
                acquisition_refined=True
    rms=float(np.sqrt(np.mean(residual**2)))
    slope_std=max(0.1/fs,rms)/float(np.sqrt(np.sum((starts-starts.mean())**2)))
    result['clock']=dict(alpha=float(alpha),alpha_std=float(slope_std),relative_rate_ppm=float((alpha-1)*1e6),
        intercept_s=float(intercept),intercept_includes_propagation=True,
        pilot_residual_rms_s=rms,pilot_residual_max_s=float(np.max(np.abs(residual))),
        pilot_arrivals_receiver_s=train.tolist(),pilot_residuals_s=residual.tolist(),
        correction='affine_waveform_resampling',absolute_source_rate_calibrated=False,
        acquisition_template_rate_refined=acquisition_refined)
    if abs(alpha-1)>.005:
        return reject('clock_rate_out_of_bounds','Relative rate exceeds the configured 5000 ppm bound.')
    if np.max(np.abs(residual))>max(2/fs,.00010):
        return reject('nonaffine_clock_or_motion','Pilots violate affine timing; movement, clock warp, gaps or overlapping reverberant tails are possible.')
    # Detect a weak earlier repeatable arrival without silently promoting it to direct.
    # Guard against the emitted pulse's own sidelobes using its autocorrelation.
    guard_s=.001
    autocorrelation=np.abs(correlate(template,template,mode='full',method='fft'))
    center=len(template)-1
    sidelobe_bound=float(np.max(autocorrelation[:max(1,center-round(guard_s*fs))])/max(autocorrelation[center],1e-15))
    earlier_threshold=max(float(envelope.max())*max(.015,5*sidelobe_bound),floor+15*max(spread,1e-12))
    weaker_peaks,_=find_peaks(envelope,height=earlier_threshold,distance=max(1,round(fs*.0003)))
    prior=weaker_peaks[(weaker_peaks/fs<train[0]-guard_s)&(weaker_peaks/fs>train[0]-p['max_echo_delay_s'])]
    suspect=[]
    for early in prior[:128]:
        expected=early/fs+alpha*(starts-starts[0])
        support=sum(bool(np.any(np.abs(weaker_peaks/fs-arrival)<max(3/fs,.00015))) for arrival in expected)
        if support>=math.ceil(.7*len(starts)):
            suspect.append(float(early/fs-train[0]))
    if suspect:
        result['direct_reference_alternatives_s']=suspect[:8]
        return reject('direct_reference_ambiguous','Weaker repeatable arrivals precede the selected reference; direct sound is not reliably identified. Reposition for clear line of sight or qualify source/band.')
    # Reacquire after rate correction: local segments avoid interpolating long silence.
    margin=.004
    local_t=np.arange(-round(margin*src_fs),round((p['duration_s']+p['max_echo_delay_s']+margin)*src_fs))/src_fs
    responses=[]
    energy=float(np.dot(pulse,pulse))
    for start in starts:
        if cancel and cancel():
            return reject('cancelled','Processing cancelled.')
        receiver_t=alpha*(start+local_t)+intercept
        if receiver_t[0]<0 or receiver_t[-1]>(len(y)-1)/fs:
            return reject('truncated_probe','Full response window missing.')
        segment=np.interp(receiver_t*fs,np.arange(len(y)),y)
        responses.append(correlate(segment,pulse,mode='valid',method='fft')/energy)
    responses=np.asarray(responses)
    response=np.median(responses,axis=0)
    envelope=np.abs(response)
    zero=round(margin*src_fs)
    direct_window=slice(max(0,zero-round(.001*src_fs)),zero+round(.001*src_fs)+1)
    direct_index=int(np.argmax(envelope[direct_window]))+direct_window.start
    direct_sample=_peak_time(envelope,direct_index)
    direct_amp=float(envelope[direct_index])
    noise_floor=float(np.median(np.abs(responses-response)))
    if direct_amp<max(10*noise_floor,.002):
        return reject('weak_direct','Direct pilot is below reliable extraction threshold.')
    direct_per_repeat=[]
    for response_i in responses:
        e=np.abs(response_i)
        j=int(np.argmax(e[direct_window]))+direct_window.start
        direct_per_repeat.append(_peak_time(e,j)/src_fs)
    timing_floor=max(.5/src_fs,.5/(p['high_hz']-p['low_hz']))
    direct_std=max(timing_floor,float(np.std(direct_per_repeat,ddof=1)))
    result['direct_std_s']=direct_std
    min_delay=max(.00035,3/(p['high_hz']-p['low_hz']))
    # This intentionally rejects weak sidelobes; sensitivity is qualified on data.
    threshold=max(float(envelope.max())*.07,noise_floor*12)
    candidate_indices,properties=find_peaks(envelope,height=threshold,
        prominence=threshold*.65,distance=max(2,round(min_delay*src_fs)))
    candidates=[]
    for index in candidate_indices:
        delay=(_peak_time(envelope,int(index))-direct_sample)/src_fs
        if not min_delay<=delay<=p['max_echo_delay_s']:
            continue
        values=np.abs(responses[:,index])
        repeat_support=int(np.count_nonzero(values>threshold*.65))
        if repeat_support<math.ceil(.7*len(responses)):
            continue
        local_delays=[]
        radius=round(.00015*src_fs)
        for r in responses:
            left=max(0,index-radius);right=min(len(r),index+radius+1)
            j=left+int(np.argmax(np.abs(r[left:right])))
            local_delays.append((_peak_time(np.abs(r),j)-direct_sample)/src_fs)
        std=max(timing_floor,float(np.std(local_delays,ddof=1)))
        candidates.append(dict(delay_s=float(delay),delay_std_s=float(std),amplitude=float(envelope[index]/direct_amp),
                               repeat_support=repeat_support,repeat_count=len(responses)))
    if len(candidates)>18:
        result['diagnostics'].append(dict(code='candidate_budget',message='Strongest 18 repeatable paths retained.'))
        candidates=sorted(candidates,key=lambda z:z['amplitude'],reverse=True)[:18]
    candidates.sort(key=lambda z:z['delay_s'])
    for i,candidate in enumerate(candidates):
        candidate['candidate_id']=f'{capture_id}:echo:{i:02d}'
    result.update(status='ok',candidates=candidates,
        quality=dict(clipped_fraction=clipped,noise_response_amplitude=noise_floor,
                     direct_response_amplitude=direct_amp,usable_band_hz=[p['low_hz'],p['high_hz']],
                     minimum_resolved_excess_delay_s=min_delay),
        response=dict(delay_unit='source_buffer_seconds',sample_rate_hz=src_fs,
                      start_delay_s=-direct_sample/src_fs,values=response.tolist()),
        direct_arrival_receiver_s=float(intercept+alpha*(starts[0]+direct_sample/src_fs-margin)))
    if estimator=='joint_kernel':
        from .joint_kernel import extract,FitCancelled
        try:
            fitted,metadata=extract(result,responses,p['high_hz']-p['low_hz'],p['max_echo_delay_s'],cancel=cancel)
        except FitCancelled:
            result.update(status='rejected',candidates=[])
            return reject('cancelled','Processing cancelled during joint waveform fitting.')
        accepted=[];unmodeled=[]
        for candidate in fitted:
            if candidate['repeat_support']<math.ceil(.7*candidate['repeat_count']):
                candidate['reason']='nonrepeatable_joint_fit';unmodeled.append(candidate)
            elif candidate.pop('unmodeled'):
                candidate['reason']='waveform_shape_mismatch';unmodeled.append(candidate)
            else:
                candidate['candidate_id']=f'{capture_id}:joint:{len(accepted):02d}'
                accepted.append(candidate)
        result.update(candidates=accepted,unmodeled_candidates=unmodeled,joint_fit=metadata)
        result['diagnostics'].append(dict(code='experimental_joint_kernel',message='Joint direct-kernel fit assumes common path waveform; repeated-fit covariance does not certify source-model or propagation accuracy.'))
    result['diagnostics'].append(dict(code='direct_path_assumed',message='Earliest significant repeatable arrival is assumed direct; obstruction and directional source bias remain uncalibrated.'))
    if not candidates:
        result['diagnostics'].append(dict(code='no_resolved_echoes',message='No repeatable separated echoes; this does not establish empty space.'))
    return result
