"""Lossless measured-array PNG and self-contained quantitative inspection."""
import base64
import colorsys
import hashlib
from html import escape
import json
import re
from pathlib import Path
import struct
import zlib
import numpy as np

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


def save_display(destination,volume,depth,amplitude,report):
    color,gray=display_arrays(depth,amplitude)
    images=[]
    for name,array in [('depth-amplitude.png',color),('amplitude.png',gray)]:
        raw=png_bytes(array)
        with (destination/name).open('xb') as f:f.write(raw)
        images.append('data:image/png;base64,'+base64.b64encode(raw).decode())
    stops=[]
    for i in range(21):
        rgb=tuple(round(v*255) for v in colorsys.hsv_to_rgb(.8*i/20,1,1));stops.append('rgb('+','.join(map(str,rgb))+') '+str(i*5)+'%')
    legend='linear-gradient(to right,'+','.join(stops)+')'
    results=report['result'];source=report['source'];limits=''.join('<li>'+escape(x)+'</li>' for x in report['limits'][:5])
    raw,axial=axial_display(volume,report['coordinates']['depth_bin_spacing_m'])
    with (destination/'axial-display.bin').open('xb') as f:f.write(raw)
    report['axial_display']=axial
    html='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>EchoSight / PHANTOM measured NLOS</title><style>
:root{font:16px/1.55 system-ui,sans-serif;color:#23262e;background:white}*{box-sizing:border-box}body{margin:0}main{max-width:1350px;margin:auto;padding:24px}header{border-bottom:2px solid #23262e;padding-bottom:18px}h1{font-size:30px;line-height:1.15;margin:8px 0}h2{font-size:19px}p{max-width:1050px}.meta,code{font:12px/1.5 ui-monospace,monospace;overflow-wrap:anywhere}.geometry{display:grid;grid-template-columns:1fr 1fr;gap:28px;margin-top:22px}figure{margin:0}img{display:block;width:100%;image-rendering:pixelated;background:black;aspect-ratio:1}.legend{height:18px;margin-top:12px}.ticks,.xaxis{display:flex;justify-content:space-between;font:12px ui-monospace,monospace}.legend-label{font-size:13px}.limits{border-top:1px solid #aab0bb;margin-top:28px;padding-top:14px}details{border-top:1px solid #aab0bb;padding:16px 0}summary{cursor:pointer;font-weight:600}li{margin:7px 0}a{color:#4d36a3}table{border-collapse:collapse;font-size:14px}td,th{padding:9px;text-align:left;border-bottom:1px solid #d8dbe1}summary:focus-visible,a:focus-visible{outline:3px solid #4d36a3;outline-offset:3px}@media(max-width:700px){main{padding:18px 14px}.geometry{grid-template-columns:1fr}h1{font-size:26px}}
</style><main><header><span class="meta">ECHOSIGHT / PHANTOM · EXTERNAL MEASURED DATA</span><h1>The measured scene, reconstructed offline.</h1><p>Published Figure 2 data and released f-k code route. Native 55 × 55 scan positions, with phase retained. This is a source-method baseline, separate from EchoSight's room pipeline and simulated room demo.</p></header><section class="geometry"><figure><h2>Depth-colored amplitude</h2><img alt="Actual measured-scene reconstruction; source threshold depth colors over amplitude" src="IMAGE0"><div class="xaxis"><span>−0.21 m</span><span>source x</span><span>+0.21 m</span></div><div class="legend" style="background:LEGEND"></div><div class="ticks"><span>1.1</span><span>1.2</span><span>1.3</span><span>1.4</span><span>1.5</span><span>1.6 m</span></div><p class="legend-label">Hue: source depth convention. Brightness: amplitude. Black: no threshold crossing or zero display amplitude. No zero-depth substitution.</p></figure><figure><h2>Maximum amplitude</h2><img alt="Linear normalized axial maximum amplitude from actual measured input" src="IMAGE1"><div class="xaxis"><span>−0.21 m</span><span>source x</span><span>+0.21 m</span></div><p class="legend-label">Linear normalized amplitude, black minimum to white maximum. Source display y increases from −0.21 m at top to +0.21 m at bottom. Both images use nearest-neighbor enlargement, adding no spatial detail.</p></figure></section><h2>Recorded reconstruction</h2><table><tr><th>Volume</th><td>3125 × 55 × 55 float64 bins</td></tr><tr><th>Threshold depths</th><td>DEPTHRANGE; COUNT of 3025 pixels</td></tr><tr><th>Depth-bin spacing</th><td>1.372 mm under source c=343 m/s and dt=8 μs. Not measured resolution.</td></tr><tr><th>Coordinates</th><td>Unregistered source plane and first 1-based global-threshold crossing. No calibrated room/world transform.</td></tr></table><section class="limits"><h2>Interpretation limits</h2><ul>LIMITS</ul></section><details><summary>Source identity and saved arrays</summary><p>Input SHA-256</p><code>HASH</code><p><a href="https://researchdata.gla.ac.uk/2046/">Official measured data/code</a> · <a href="https://doi.org/10.1038/s42005-025-02335-3">Li et al. 2025 paper</a> · CC BY4.0. Array identities and all output hashes are recorded in report.json. volume.npy,depth_m.npy and maximum_amplitude.npy retain numerical values; PNGs are displays.</p></details></main></html>'''
    lo,hi=results['depth_min_m'],results['depth_max_m']
    depth_range='no crossing' if lo is None else f'{lo:.6f}–{hi:.6f} m under the source convention'
    # Embed source-bound native depth slices, so file inspection needs no server,
    # dependencies or fetch. Full-precision scientific arrays remain separate.
    panel='''<section><h2>Inspect native axial amplitude slices</h2><p>Scrub consecutive source depth bins from about 1.0 to 1.7 m. These are slices through the reconstructed volume, not filled surfaces. Click a pixel or focus the image and use arrow keys to inspect its source-array location.</p><label for="depth-bin">Source depth slice</label> <input id="depth-bin" type="range" min="0" max="MAXFRAME" value="MIDFRAME" style="width:min(600px,100%)"><output id="slice-label"></output><div style="display:grid;grid-template-columns:minmax(0,550px) minmax(180px,1fr);gap:24px" class="slice-layout"><canvas id="axial" width="55" height="55" tabindex="0" role="img" aria-label="Native axial amplitude; click or arrow keys to inspect pixels" style="width:100%;image-rendering:pixelated;aspect-ratio:1;background:black"></canvas><div><output id="pixel" aria-live="polite"></output><p class="meta">Amplitude display uses 8 bits and the global volume maximum. Full precision: volume.npy. Gray 0 can mean amplitude rounded to zero. It is not a free-space determination.</p><p class="meta">Embedded native-slice bytes SHA-256<br>SLICEHASH</p></div></div></section>
<script>"use strict";
const bytes=Uint8Array.from(atob("FRAMEBYTES"),c=>c.charCodeAt(0));
const spec=AXIALSPEC, depths=DEPTHVALUES;
const slider=document.getElementById('depth-bin'),canvas=document.getElementById('axial'),ctx=canvas.getContext('2d');let px=27,py=27;
function draw(){const frame=Number(slider.value),bin=spec.first_volume_index_zero_based+frame,z=(bin+1)*spec.depth_bin_spacing_m;const image=ctx.createImageData(55,55);for(let i=0;i<3025;i++){const v=bytes[frame*3025+i];image.data[i*4]=v;image.data[i*4+1]=v;image.data[i*4+2]=v;image.data[i*4+3]=255;}ctx.putImageData(image,0,0);ctx.strokeStyle='#ffbf00';ctx.lineWidth=.2;ctx.strokeRect(px,py,1,1);const value=bytes[frame*3025+py*55+px],first=depths[py][px];document.getElementById('slice-label').textContent=' '+z.toFixed(6)+' m / source bin '+(bin+1);document.getElementById('pixel').textContent='Source coordinates: x='+(-.21+px*.42/54).toFixed(6)+' m, y='+(-.21+py*.42/54).toFixed(6)+' m; slice depth='+z.toFixed(6)+' m. volume.npy['+bin+','+(54-py)+','+(54-px)+']. Display amplitude='+value+'/255. First threshold source depth: '+(first===null?'unknown':first.toFixed(6)+' m')+'. Unregistered coordinates.';}
slider.addEventListener('input',draw);canvas.addEventListener('click',e=>{const r=canvas.getBoundingClientRect();px=Math.max(0,Math.min(54,Math.floor((e.clientX-r.left)*55/r.width)));py=Math.max(0,Math.min(54,Math.floor((e.clientY-r.top)*55/r.height)));canvas.focus();draw();});canvas.addEventListener('keydown',e=>{const moves={ArrowLeft:[-1,0],ArrowRight:[1,0],ArrowUp:[0,-1],ArrowDown:[0,1]};if(moves[e.key]){e.preventDefault();px=Math.max(0,Math.min(54,px+moves[e.key][0]));py=Math.max(0,Math.min(54,py+moves[e.key][1]));draw();}});draw();
</script>'''
    depth_values=np.flip(depth,axis=(0,1))
    values=[[float(v) if np.isfinite(v) else None for v in row] for row in depth_values]
    panel=substitute(panel,{'MAXFRAME':str(axial['frame_count']-1),'MIDFRAME':str(axial['frame_count']//2),'SLICEHASH':axial['sha256'],'FRAMEBYTES':base64.b64encode(raw).decode(),'AXIALSPEC':json.dumps(axial,allow_nan=False),'DEPTHVALUES':json.dumps(values,allow_nan=False)})
    html=html.replace('@media(max-width:700px){','@media(max-width:700px){.slice-layout{grid-template-columns:1fr!important}')
    html=substitute(html,{'IMAGE0':images[0],'IMAGE1':images[1],'LEGEND':legend,'DEPTHRANGE':escape(depth_range),'COUNT':str(results['finite_depth_pixels']),'LIMITS':limits,'HASH':source['sha256']})
    html=html.replace('<section class="limits">',panel+'<section class="limits">')
    with (destination/'inspection.html').open('x',encoding='utf-8') as f:f.write(html)
