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
<section aria-labelledby="profile-title"><h2 id="profile-title">Selected pixel: axial profile and threshold sensitivity</h2><p>The curve uses the same consecutive, 8-bit display frames as the slice viewer, only inside the plotted depth window. Markers and the table use the full-precision <strong>full volume</strong>, before quantization. A rounded curve can appear to cross a threshold at a different bin.</p><canvas id="profile" role="img" aria-label="Selected pixel axial amplitude profile; exact native decisions and plotted window are listed below" style="display:block;width:100%;height:280px"></canvas><p class="meta">Black: display amplitude /255 · Purple: default 4.5 threshold and its exact native first crossing · Gray: other native crossings · Amber: current slice</p><p id="profile-summary" class="meta"></p><div style="overflow-x:auto"><table id="threshold-table"><caption>Full-precision, full-volume strict threshold crossings at this pixel</caption><thead><tr><th>Divisor</th><th>Native amplitude threshold</th><th>First source bin / depth</th><th>In plotted window?</th></tr></thead><tbody></tbody></table></div><p id="profile-peak" class="meta"></p><p>Range across these rules is <strong>threshold sensitivity</strong>. It is not confidence, physical surface truth, uncertainty or resolution. Missing crossings stay unknown; an axial maximum alone is not a detection. Unregistered source coordinates remain unchanged.</p><p class="meta">Diagnostic grid: full-precision crossings and first axial maximum, <a href="threshold-diagnostics.json">threshold-diagnostics.json</a><br>SHA-256 DIAGNOSTICHASH</p></section>
<script>"use strict";
const bytes=Uint8Array.from(atob("FRAMEBYTES"),c=>c.charCodeAt(0));
const spec=AXIALSPEC, depths=DEPTHVALUES;
const diagnostic=THRESHOLDDATA;
const slider=document.getElementById('depth-bin'),canvas=document.getElementById('axial'),ctx=canvas.getContext('2d');let px=27,py=27;
function sourceDepth(index){return (index+1)*spec.depth_bin_spacing_m;}
function inWindow(index){return index!==null&&index>=spec.first_volume_index_zero_based&&index<spec.first_volume_index_zero_based+spec.frame_count;}
function inspectPixel(){return {crossings:diagnostic.first_crossing_volume_indices.map(grid=>grid[py][px]),peak:diagnostic.axial_maximum_volume_indices[py][px],maximum:diagnostic.axial_maximum_amplitudes[py][px]};}
function drawProfile(frame){
 const graph=document.getElementById('profile'),g=graph.getContext('2d'),width=Math.max(260,graph.clientWidth),height=280,dpr=window.devicePixelRatio||1;
 graph.width=Math.round(width*dpr);graph.height=Math.round(height*dpr);g.setTransform(dpr,0,0,dpr,0,0);g.clearRect(0,0,width,height);g.font='12px system-ui';
 const left=49,right=14,top=26,bottom=48,pw=width-left-right,ph=height-top-bottom,start=spec.first_volume_index_zero_based,last=start+spec.frame_count-1;
 const xx=index=>left+(index-start)/Math.max(1,spec.frame_count-1)*pw,yy=value=>top+(1-value/255)*ph;
 g.fillStyle='#23262e';g.fillText('Global-normalized amplitude (8-bit)',left,15);g.strokeStyle='#d8dbe1';g.lineWidth=1;
 for(const value of [0,64,128,192,255]){g.beginPath();g.moveTo(left,yy(value));g.lineTo(width-right,yy(value));g.stroke();g.fillText(String(value),9,yy(value)+4);}
 g.strokeStyle='#23262e';g.beginPath();g.moveTo(left,top);g.lineTo(left,top+ph);g.lineTo(width-right,top+ph);g.stroke();
 const ticks=width<500?2:4;for(let i=0;i<=ticks;i++){const index=start+(last-start)*i/ticks;g.textAlign=i===0?'left':i===ticks?'right':'center';g.fillText(sourceDepth(index).toFixed(3),xx(index),height-27);}g.textAlign='left';g.fillText('Source depth (m), unregistered',left,height-7);
 g.strokeStyle='#23262e';g.lineWidth=1.4;g.beginPath();for(let i=0;i<spec.frame_count;i++){const y=yy(bytes[i*3025+py*55+px]);if(i===0)g.moveTo(xx(start+i),y);else g.lineTo(xx(start+i),y);}g.stroke();
 const selected=inspectPixel();
 g.strokeStyle='#4d36a3';g.lineWidth=1;g.setLineDash([5,4]);g.beginPath();g.moveTo(left,yy(255/4.5));g.lineTo(width-right,yy(255/4.5));g.stroke();
 selected.crossings.forEach((index,k)=>{if(!inWindow(index))return;g.strokeStyle=diagnostic.divisors[k]===4.5?'#4d36a3':'#717783';g.lineWidth=diagnostic.divisors[k]===4.5?2:1;g.setLineDash(diagnostic.divisors[k]===4.5?[]:[2,4]);g.beginPath();g.moveTo(xx(index),top);g.lineTo(xx(index),top+ph);g.stroke();});
 g.strokeStyle='#b77800';g.lineWidth=2;g.setLineDash([7,4]);g.beginPath();g.moveTo(xx(start+frame),top);g.lineTo(xx(start+frame),top+ph);g.stroke();g.setLineDash([]);
 const rows=document.querySelector('#threshold-table tbody');rows.replaceChildren();
 selected.crossings.forEach((index,k)=>{const row=document.createElement('tr');if(diagnostic.divisors[k]===4.5)row.style.fontWeight='700';const texts=[String(diagnostic.divisors[k])+(diagnostic.divisors[k]===4.5?' (default)':''),diagnostic.thresholds[k].toPrecision(7),index===null?'unknown':String(index+1)+' / '+sourceDepth(index).toFixed(6)+' m',index===null?'no crossing':inWindow(index)?'yes':'outside'];for(const text of texts){const td=document.createElement('td');td.textContent=text;row.append(td);}rows.append(row);});
 const known=selected.crossings.filter(index=>index!==null);document.getElementById('profile-summary').textContent='Pixel volume.npy[:, '+(54-py)+', '+(54-px)+']. Plotted bins '+(start+1)+'–'+(last+1)+'. '+(known.length?'Threshold sensitivity: '+sourceDepth(Math.min(...known)).toFixed(6)+'–'+sourceDepth(Math.max(...known)).toFixed(6)+' m across '+known.length+' rules.':'Threshold sensitivity: unknown; no rule crosses.')+' '+(5-known.length)+' of 5 rules have no crossing. Unknown rules are not included in the range.';
 document.getElementById('profile-peak').textContent=selected.maximum===0?'No nonzero axial maximum: all profile bins are zero. First-tie index 0 (source bin 1) is not a detected return.':'Full-volume first axial maximum: source bin '+(selected.peak+1)+' / '+sourceDepth(selected.peak).toFixed(6)+' m; native amplitude '+selected.maximum.toPrecision(7)+'; '+(inWindow(selected.peak)?'inside':'outside')+' plotted window. Ties use the first native index.';
 graph.setAttribute('aria-label','Axial display profile for native spatial index '+(54-py)+', '+(54-px)+'. '+document.getElementById('profile-summary').textContent+' Full-precision decisions follow in the table.');
}
function draw(){const frame=Number(slider.value),bin=spec.first_volume_index_zero_based+frame,z=(bin+1)*spec.depth_bin_spacing_m;const image=ctx.createImageData(55,55);for(let i=0;i<3025;i++){const v=bytes[frame*3025+i];image.data[i*4]=v;image.data[i*4+1]=v;image.data[i*4+2]=v;image.data[i*4+3]=255;}ctx.putImageData(image,0,0);ctx.strokeStyle='#ffbf00';ctx.lineWidth=.2;ctx.strokeRect(px,py,1,1);const value=bytes[frame*3025+py*55+px],first=depths[py][px];document.getElementById('slice-label').textContent=' '+z.toFixed(6)+' m / source bin '+(bin+1);document.getElementById('pixel').textContent='Source coordinates: x='+(-.21+px*.42/54).toFixed(6)+' m, y='+(-.21+py*.42/54).toFixed(6)+' m; slice depth='+z.toFixed(6)+' m. volume.npy['+bin+','+(54-py)+','+(54-px)+']. Display amplitude='+value+'/255. First threshold source depth: '+(first===null?'unknown':first.toFixed(6)+' m')+'. Unregistered coordinates.';drawProfile(frame);}
slider.addEventListener('input',draw);canvas.addEventListener('click',e=>{const r=canvas.getBoundingClientRect();px=Math.max(0,Math.min(54,Math.floor((e.clientX-r.left)*55/r.width)));py=Math.max(0,Math.min(54,Math.floor((e.clientY-r.top)*55/r.height)));canvas.focus();draw();});canvas.addEventListener('keydown',e=>{const moves={ArrowLeft:[-1,0],ArrowRight:[1,0],ArrowUp:[0,-1],ArrowDown:[0,1]};if(moves[e.key]){e.preventDefault();px=Math.max(0,Math.min(54,px+moves[e.key][0]));py=Math.max(0,Math.min(54,py+moves[e.key][1]));draw();}});window.addEventListener('resize',()=>drawProfile(Number(slider.value)));draw();
</script>'''
    depth_values=np.flip(depth,axis=(0,1))
    values=[[float(v) if np.isfinite(v) else None for v in row] for row in depth_values]
    panel=substitute(panel,{'THRESHOLDDATA':diagnostic_json,'DIAGNOSTICHASH':report['threshold_diagnostics']['sha256'],'MAXFRAME':str(axial['frame_count']-1),'MIDFRAME':str(axial['frame_count']//2),'SLICEHASH':axial['sha256'],'FRAMEBYTES':base64.b64encode(raw).decode(),'AXIALSPEC':json.dumps(axial,allow_nan=False),'DEPTHVALUES':json.dumps(values,allow_nan=False)})
    html=html.replace('@media(max-width:700px){','@media(max-width:700px){.slice-layout{grid-template-columns:1fr!important}')
    html=substitute(html,{'IMAGE0':images[0],'IMAGE1':images[1],'LEGEND':legend,'DEPTHRANGE':escape(depth_range),'COUNT':str(results['finite_depth_pixels']),'LIMITS':limits,'HASH':source['sha256']})
    html=html.replace('<section class="limits">',panel+'<section class="limits">')
    with (destination/'inspection.html').open('x',encoding='utf-8') as f:f.write(html)
