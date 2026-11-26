"use strict";

const element = id => document.getElementById(id);
const data = JSON.parse(element('inspection-data').textContent);
const {spec, depths, diagnostic} = data;
const bytes = Uint8Array.from(atob(data.frames), value => value.charCodeAt(0));
const slider = element('depth-bin');
const exactBin = element('exact-bin');
const canvas = element('axial');
const context = canvas.getContext('2d');
const xInput = element('pixel-column');
const yInput = element('pixel-row');
const zoom = element('zoom');
const firstBin = spec.first_volume_index_zero_based + 1;
const side = 55;
const planeSize = side * side;
let px = xInput.valueAsNumber, py = yInput.valueAsNumber;
let viewport = {x: 0, y: 0, size: side};

const clamp = (value, min, max) => Math.max(min, Math.min(max, value));
const sourceDepth = index => (index + 1) * spec.depth_bin_spacing_m;
const sourceXY = index => -.21 + index * .42 / (side - 1);
const axisText = index => sourceXY(index).toFixed(3).replace('-', '−');
const inWindow = index => index !== null && index >= firstBin - 1 && index < firstBin - 1 + spec.frame_count;
function inspectPixel() {
  return {
    crossings: diagnostic.first_crossing_volume_indices.map(grid => grid[py][px]),
    peak: diagnostic.axial_maximum_volume_indices[py][px],
    maximum: diagnostic.axial_maximum_amplitudes[py][px],
  };
}

function drawProfile(frame){
 const graph=document.getElementById('profile'),g=graph.getContext('2d'),width=graph.clientWidth,height=graph.clientHeight,dpr=window.devicePixelRatio||1;
 graph.width=Math.round(width*dpr);graph.height=Math.round(height*dpr);g.setTransform(dpr,0,0,dpr,0,0);g.clearRect(0,0,width,height);g.font='12px system-ui';
 const left=49,right=14,top=26,bottom=48,pw=width-left-right,ph=height-top-bottom,start=spec.first_volume_index_zero_based,last=start+spec.frame_count-1;
 const xx=index=>left+(index-start)/Math.max(1,spec.frame_count-1)*pw,yy=value=>top+(1-value/255)*ph;
 g.fillStyle='#152329';g.fillText('Normalized amplitude / 255',left,15);g.strokeStyle='#d1ded8';g.lineWidth=1;
 for(const value of [0,64,128,192,255]){g.beginPath();g.moveTo(left,yy(value));g.lineTo(width-right,yy(value));g.stroke();g.fillText(String(value),9,yy(value)+4);}
 g.strokeStyle='#152329';g.beginPath();g.moveTo(left,top);g.lineTo(left,top+ph);g.lineTo(width-right,top+ph);g.stroke();
 const ticks=width<500?2:4;for(let i=0;i<=ticks;i++){const index=start+(last-start)*i/ticks;g.textAlign=i===0?'left':i===ticks?'right':'center';g.fillText(sourceDepth(index).toFixed(3),xx(index),height-27);}g.textAlign='left';g.fillText('Source depth (m), unregistered',left,height-7);
 g.strokeStyle='#152329';g.lineWidth=1.4;g.beginPath();for(let i=0;i<spec.frame_count;i++){const y=yy(bytes[i*3025+py*55+px]);if(i===0)g.moveTo(xx(start+i),y);else g.lineTo(xx(start+i),y);}g.stroke();
 const selected=inspectPixel();
 g.strokeStyle='#116458';g.lineWidth=1;g.setLineDash([5,4]);g.beginPath();g.moveTo(left,yy(255/4.5));g.lineTo(width-right,yy(255/4.5));g.stroke();
 selected.crossings.forEach((index,k)=>{if(!inWindow(index))return;g.strokeStyle=diagnostic.divisors[k]===4.5?'#116458':'#596c70';g.lineWidth=diagnostic.divisors[k]===4.5?2:1;g.setLineDash(diagnostic.divisors[k]===4.5?[]:[2,4]);g.beginPath();g.moveTo(xx(index),top);g.lineTo(xx(index),top+ph);g.stroke();});
 g.strokeStyle='#8a5500';g.lineWidth=2;g.setLineDash([7,4]);g.beginPath();g.moveTo(xx(start+frame),top);g.lineTo(xx(start+frame),top+ph);g.stroke();g.setLineDash([]);
 const rows=document.querySelector('#threshold-table tbody');rows.replaceChildren();
 selected.crossings.forEach((index,k)=>{const row=document.createElement('tr');if(diagnostic.divisors[k]===4.5)row.style.fontWeight='700';const texts=[String(diagnostic.divisors[k])+(diagnostic.divisors[k]===4.5?' (default)':''),diagnostic.thresholds[k].toPrecision(7),index===null?'unknown':String(index+1)+' / '+sourceDepth(index).toFixed(6)+' m',index===null?'no crossing':inWindow(index)?'yes':'outside'];for(const text of texts){const td=document.createElement('td');td.textContent=text;row.append(td);}rows.append(row);});
 const known=selected.crossings.filter(index=>index!==null);document.getElementById('profile-summary').textContent='Pixel volume.npy[:, '+(54-py)+', '+(54-px)+']. Plotted bins '+(start+1)+'–'+(last+1)+'. '+(known.length?'Threshold sensitivity: '+sourceDepth(Math.min(...known)).toFixed(6)+'–'+sourceDepth(Math.max(...known)).toFixed(6)+' m across '+known.length+' rules.':'Threshold sensitivity: unknown; no rule crosses.')+' '+(5-known.length)+' of 5 rules have no crossing. Unknown rules are not included in the range.';
 document.getElementById('profile-peak').textContent=selected.maximum===0?'No nonzero axial maximum: all profile bins are zero. First-tie index 0 (source bin 1) is not a detected return.':'Full-volume first axial maximum: source bin '+(selected.peak+1)+' / '+sourceDepth(selected.peak).toFixed(6)+' m; native amplitude '+selected.maximum.toPrecision(7)+'; '+(inWindow(selected.peak)?'inside':'outside')+' plotted window. Ties use the first native index.';
 graph.setAttribute('aria-label','Axial display profile for native spatial index '+(54-py)+', '+(54-px)+'. '+document.getElementById('profile-summary').textContent+' Full-precision decisions follow in the table.');
}

function recenter() {
  if (zoom.getAttribute('aria-pressed') === 'false') {
    viewport = {x: 0, y: 0, size: side};
    return;
  }
  const size = 27;
  const radius = Math.floor(size / 2);
  viewport = {x: clamp(px - radius, 0, side - size), y: clamp(py - radius, 0, side - size), size};
}

function drawRaster(frame) {
  const {x, y, size} = viewport;
  canvas.width = size;
  canvas.height = size;
  const image = context.createImageData(size, size);
  for (let row = 0; row < size; row++) {
    for (let col = 0; col < size; col++) {
      const value = bytes[frame * planeSize + (y + row) * side + x + col];
      const index = (row * size + col) * 4;
      image.data[index] = value;
      image.data[index + 1] = value;
      image.data[index + 2] = value;
      image.data[index + 3] = 255;
    }
  }
  context.putImageData(image, 0, 0);
  const marker = element('pixel-marker');
  marker.style.left = (px - x) * 100 / size + '%';
  marker.style.top = (py - y) * 100 / size + '%';
  marker.style.width = marker.style.height = 100 / size + '%';
  for (const [axis, start] of [['x', x], ['y', y]]) {
    element(axis + '-start').textContent = axisText(start);
    element(axis + '-end').textContent = axisText(start + size - 1);
  }
}

function draw() {
  const frame = Number(slider.value);
  const bin = firstBin + frame;
  const depth = sourceDepth(bin - 1).toFixed(6);
  drawRaster(frame);
  const value = bytes[frame * planeSize + py * side + px];
  const first = depths[py][px];
  const binLabel = depth + ' m · bin ' + bin;
  element('slice-label').textContent = binLabel;
  slider.setAttribute('aria-valuetext', binLabel);
  element('amplitude').textContent = value + ' / 255';
  element('first-depth').textContent = first === null ? 'Unknown' : first.toFixed(6) + ' m';
  element('pixel').textContent = 'Source x ' + sourceXY(px).toFixed(6) + ' m · y ' + sourceXY(py).toFixed(6) + ' m · volume.npy[' + (bin - 1) + ', ' + (side - 1 - py) + ', ' + (side - 1 - px) + ']';
  exactBin.value = bin;
  xInput.value = px;
  yInput.value = py;
  const prev = element('prev-bin'), next = element('next-bin');
  prev.disabled = frame === 0;
  next.disabled = frame === spec.frame_count - 1;
  drawProfile(frame);
}

function selectFrame(frame) {
  slider.value = clamp(frame, 0, spec.frame_count - 1);
  draw();
}

function inputValue(field, previous) {
  return Number.isFinite(field.valueAsNumber) ? Math.round(field.valueAsNumber) : previous;
}

function selectPixel(x, y) {
  px = clamp(x, 0, side - 1);
  py = clamp(y, 0, side - 1);
  if (px < viewport.x || px >= viewport.x + viewport.size ||
      py < viewport.y || py >= viewport.y + viewport.size) recenter();
  draw();
}

slider.addEventListener('input', draw);
exactBin.addEventListener('change', () => selectFrame(inputValue(exactBin, firstBin + Number(slider.value)) - firstBin));
element('prev-bin').addEventListener('click', () => selectFrame(Number(slider.value) - 1));
element('next-bin').addEventListener('click', () => selectFrame(Number(slider.value) + 1));
xInput.addEventListener('change', () => selectPixel(inputValue(xInput, px), py));
yInput.addEventListener('change', () => selectPixel(px, inputValue(yInput, py)));
zoom.addEventListener('click', () => {
  const active = zoom.getAttribute('aria-pressed') === 'true';
  zoom.setAttribute('aria-pressed', String(!active));
  recenter();
  draw();
});
canvas.addEventListener('click', event => {
  const bounds = canvas.getBoundingClientRect();
  const projectedX = Math.floor((event.clientX - bounds.left) * viewport.size / bounds.width);
  const projectedY = Math.floor((event.clientY - bounds.top) * viewport.size / bounds.height);
  canvas.focus();
  selectPixel(viewport.x + projectedX, viewport.y + projectedY);
});
canvas.addEventListener('keydown', event => {
  const moves = {ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1]};
  if (!Object.hasOwn(moves, event.key)) return;
  event.preventDefault();
  selectPixel(px + moves[event.key][0], py + moves[event.key][1]);
});
window.addEventListener('resize', () => drawProfile(Number(slider.value)));
element('axial-view').hidden = false;
element('axial-link').hidden = false;
draw();
