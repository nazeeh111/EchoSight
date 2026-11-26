"""Lossless measured-array PNG and self-contained quantitative inspection."""
import colorsys
import hashlib
import json
import re
import struct
import zlib
import numpy as np

from .nlos_inspection import render_inspection

def substitute(template,values):
    # One pass: inserted base64/numeric data must never be rescanned as tokens.
    return re.sub('|'.join(re.escape(k) for k in values),lambda m:values[m.group()],template)


def png_bytes(rgb):
    rgb=np.asarray(rgb)
    if rgb.ndim!=3 or rgb.shape[2]!=3 or rgb.dtype!=np.uint8:raise ValueError('PNG needs uint8 RGB pixels')
    def chunk(tag,data):return struct.pack('>I',len(data))+tag+data+struct.pack('>I',zlib.crc32(tag+data)&0xffffffff)
    raw=b''.join(b'\0'+row.tobytes() for row in rgb)
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',rgb.shape[1],rgb.shape[0],8,2,0,0,0))+chunk(b'IDAT',zlib.compress(raw))+chunk(b'IEND',b'')


def display_arrays(depth,amplitude):
    if depth.shape!=amplitude.shape or depth.ndim!=2:raise ValueError('Display arrays disagree')
    low=float(amplitude.min());span=float(amplitude.max()-low)
    norm=(amplitude-low)/span if span else np.zeros_like(amplitude)
    color=np.zeros((*depth.shape,3),dtype=np.uint8)
    for y,x in np.ndindex(depth.shape):
        if np.isfinite(depth[y,x]):
            hue=.8*(depth[y,x]-1.1)/.5
            color[y,x]=np.rint(np.array(colorsys.hsv_to_rgb(float(hue%1),1,float(min(1,1.5*norm[y,x]))))*255)
    gray=np.repeat(np.rint(np.clip(norm,0,1)*255).astype(np.uint8)[:,:,None],3,axis=2)
    return np.flip(color,axis=(0,1)).copy(),np.flip(gray,axis=(0,1)).copy()


def axial_display(volume,spacing):
    """Native consecutive source bins, only display-quantized; no new voxels."""
    start=max(0,int(np.ceil(1.0/spacing))-1)
    stop=min(len(volume),int(np.floor(1.7/spacing)))
    maximum=float(volume.max())
    frames=np.rint(np.clip(volume[start:stop]/maximum if maximum else volume[start:stop],0,1)*255).astype(np.uint8)
    frames=np.flip(frames,axis=(1,2)).copy()
    raw=frames.tobytes()
    return raw,{'first_volume_index_zero_based':start,'frame_count':len(frames),'shape':list(frames.shape),
        'depth_bin_spacing_m':spacing,'depth_formula':'(first_volume_index_zero_based+slider_index+1)*depth_bin_spacing_m',
        'lateral_display':'both native array axes reversed; source x/y span[-.21,.21]m, y increases downward',
        'display_quantization':'round(clip(native amplitude/global volume maximum,0,1)*255); uint8, C-order',
        'global_volume_maximum':maximum,'sha256':hashlib.sha256(raw).hexdigest()}


THRESHOLD_DIVISORS=(3,4,4.5,5,6)

def threshold_diagnostics(volume,spacing):
    """Full-precision rules over the full volume; grids follow displayed xy."""
    if volume.ndim!=3 or any(v==0 for v in volume.shape) or not np.isfinite(volume).all() or np.any(volume<0):
        raise ValueError('Threshold inspection requires a finite nonnegative nonempty volume')
    if not np.isfinite(spacing) or spacing<=0:raise ValueError('Positive finite source spacing required')
    maximum=float(volume.max());crossings=[]
    for divisor in THRESHOLD_DIVISORS:
        detected=volume>maximum/divisor
        first=detected.argmax(axis=0).astype(object)
        first[~detected.any(axis=0)]=None
        crossings.append(np.flip(first,axis=(0,1)).tolist())
    return {'schema':'echosight.nlos-threshold-diagnostics/1',
        'divisors':list(THRESHOLD_DIVISORS),'default_divisor':4.5,
        'thresholds':[maximum/divisor for divisor in THRESHOLD_DIVISORS],
        'global_volume_maximum':maximum,'volume_shape':list(volume.shape),
        'depth_bin_spacing_m':float(spacing),
        'index_convention':'zero-based native volume depth indices; source depth=(index+1)*spacing; null=no strict crossing',
        'grid_convention':'display rows/columns, both native spatial axes reversed',
        'first_crossing_volume_indices':crossings,
        'axial_maximum_volume_indices':np.flip(volume.argmax(axis=0),axis=(0,1)).tolist(),
        'axial_maximum_amplitudes':np.flip(volume.max(axis=0),axis=(0,1)).tolist(),
        'peak_rule':'first full-volume maximum; index0 for all-zero profiles is not a detection',
        'interpretation':'Threshold sensitivity only, not confidence, physical surface, uncertainty or resolution'}


def save_display(destination,volume,depth,amplitude,report):
    diagnostics=threshold_diagnostics(volume,report['coordinates']['depth_bin_spacing_m'])
    diagnostic_json=json.dumps(diagnostics,separators=(',',':'),allow_nan=False)
    diagnostic_bytes=(diagnostic_json+'\n').encode('utf-8')
    with (destination/'threshold-diagnostics.json').open('xb') as f:f.write(diagnostic_bytes)
    report['threshold_diagnostics']={'file':'threshold-diagnostics.json','schema':diagnostics['schema'],
        'bytes':len(diagnostic_bytes),'sha256':hashlib.sha256(diagnostic_bytes).hexdigest(),
        'source':'full-precision full volume, before display quantization; same source axes and depth convention',
        'divisors':list(THRESHOLD_DIVISORS),'default_divisor':4.5,'interpretation':diagnostics['interpretation']}
    color,gray=display_arrays(depth,amplitude)
    images=[]
    for name,array in [('depth-amplitude.png',color),('amplitude.png',gray)]:
        raw=png_bytes(array)
        with (destination/name).open('xb') as f:f.write(raw)
        images.append(raw)
    stops=[]
    for i in range(21):
        rgb=tuple(round(v*255) for v in colorsys.hsv_to_rgb(.8*i/20,1,1));stops.append('rgb('+','.join(map(str,rgb))+') '+str(i*5)+'%')
    legend='linear-gradient(to right,'+','.join(stops)+')'
    raw,axial=axial_display(volume,report['coordinates']['depth_bin_spacing_m'])
    with (destination/'axial-display.bin').open('xb') as f:f.write(raw)
    report['axial_display']=axial
    depth_values = np.flip(depth, axis=(0, 1))
    values = [[float(value) if np.isfinite(value) else None for value in row] for row in depth_values]
    html = render_inspection(
        axial=axial, frames=raw, depths=values, diagnostic=diagnostics,
        diagnostic_hash=report['threshold_diagnostics']['sha256'],
        images=images, legend=legend, results=report['result'],
        source_hash=report['source']['sha256'], limits=report['limits'][:5],
    )
    with (destination/'inspection.html').open('x',encoding='utf-8') as f:f.write(html)
