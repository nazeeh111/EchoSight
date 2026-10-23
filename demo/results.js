import { validateResult, displayedSurfaces, evidenceRows, MAX_RESULT_BYTES, displayText } from './result-data.js';
import { ResultView } from './result-view.js';
const $ = selector => document.querySelector(selector);
const element = (tag, text) => { const node = document.createElement(tag); if (text !== undefined) node.textContent = String(text); return node; };
const label = value => displayText(value);
const number = (value, digits = 3) => typeof value === 'number' && Number.isFinite(value) ? value.toFixed(digits) : 'Unavailable';
let result, current = [], currentAlternative = false, currentHypothesis = null, loadVersion = 0, view;
const resultListeners = new Set();
try { view = new ResultView($('#result-canvas'), surface => selectSurface(String(current.indexOf(surface)))); }
catch { $('#render-status').textContent = 'WebGL is unavailable. You can still inspect surfaces and their evidence below.'; }
function notice(message, error = false) { $('#result-notice').textContent = message; $('#result-notice').dataset.error = error; }
function pair(dl, name, value) { dl.append(element('dt', name), element('dd', value)); }
function list(target, values, fallback) {
  target.replaceChildren(...(values.length ? values.map(value => element('li', label(value))) : [element('li', fallback)]));
}
function selectSurface(index) {
  const surface = current[index];
  $('#result-surface').value = surface ? String(current.indexOf(surface)) : '';
  view?.select(surface);
  const detail = $('#surface-detail'); detail.replaceChildren();
  if (!surface) {
    detail.append(element('p', 'Choose a surface to inspect its uncertainty and linked echoes.'));
    if (currentHypothesis) {
      detail.append(element('h3', 'Supplied alternative geometry · unconfirmed'));
      detail.append(element('p', 'Planes have no inferred extent. Image sources are model explanations, not physical emitters. Coordinates below are supplied by this hypothesis in metres, Z up.'));
      detail.append(element('pre', displayText({ planes: currentHypothesis.planes ?? [], image_sources_m: currentHypothesis.image_sources_m ?? [] }, 16000, true)));
    }
    return;
  }
  const dl = element('dl');
  pair(dl, 'Surface', surface.surface_id);
  pair(dl, 'Normal (x, y, z)', surface.normal.map(n => number(n, 4)).join(', '));
  pair(dl, 'Plane offset', `${number(surface.offset_m)} m`);
  pair(dl, 'Offset standard deviation', `${number(surface.uncertainty.offset_std_m, 5)} m`);
  pair(dl, 'Normal standard deviation', surface.uncertainty.normal_angular_std_rad == null ? 'Unavailable' : `${number(surface.uncertainty.normal_angular_std_rad, 5)} rad`);
  pair(dl, 'Physical extent', 'Unknown; support hull only');
  pair(dl, 'Linked echoes', surface.support.length);
  detail.append(dl, element('p', 'Standard deviations are local and conditional on this model and echo assignment. They exclude unmodeled bias and competing interpretations.'));
  const rows = evidenceRows(result, surface);
  detail.append(element('h3', 'Echo evidence · source-buffer milliseconds'));
  const wrapper = element('div'); wrapper.className = 'evidence-scroll';
  const table = element('table'), head = element('thead'), header = element('tr');
  for (const name of ['Capture / candidate', 'Observed', 'Predicted', 'Residual']) { const th = element('th', name); th.scope = 'col'; header.append(th); }
  head.append(header); table.append(head); const body = element('tbody');
  for (const row of rows) {
    const tr = element('tr');
    for (const value of [`${row.capture_id} / ${row.candidate_id}`, number(row.observed_ms), number(row.predicted_ms), number(row.residual_ms, 4)]) tr.append(element('td', value));
    body.append(tr);
  }
  table.append(body); wrapper.append(table); detail.append(wrapper);
  detail.append(element('p', rows.some(row => !row.source || !row.receiver) ? 'Some surveyed poses are missing; only available reflection points are drawn. No ray endpoint is invented.' : 'White paths connect supplied source and receiver poses through the inferred reflection points. These are conditional first-order ray paths.'));
  const entries = result.interpretation?.surface_interpretations;
  const interpretation = !currentAlternative && Array.isArray(entries) ? entries.find(entry => entry?.surface_id === surface.surface_id) : null;
  detail.append(element('h3', 'Material and appearance context'));
  if (interpretation) {
    detail.append(element('p', 'Reference-library material comparisons are conditional. Appearance is supplied context; sound does not measure optical color. Display patch colors above are unrelated.'));
    const pre = element('pre', displayText({ material: interpretation.material, appearance: interpretation.appearance }, 8000, true));
    detail.append(pre);
  } else detail.append(element('p', 'No interpretation entry is supplied for this surface. Material and optical color remain unknown.'));
}
function choose(choice) {
  const display = displayedSurfaces(result, choice);
  view?.setResult(result, display.surfaces, display.alternative);
  current = display.surfaces; currentAlternative = display.alternative;
  currentHypothesis = display.alternative ? result.hypotheses[Number(choice)] : null;
  $('#hypothesis-notice').hidden = !display.alternative;
  $('#hypothesis-notice').textContent = `ALTERNATIVE HYPOTHESIS · ${label(display.note)} Never combined with definitive surfaces.`;
  $('#result-empty').hidden = current.some(surface => surface.triangles.length > 0) && !!view;
  $('#result-empty').textContent = !view ? '3D unavailable. Surface evidence is available in the inspector.' : display.alternative ? 'This hypothesis has no supplied surface mesh. Bare planes and image sources are not expanded into invented patches.' : result.status === 'ambiguous' ? 'Geometry is ambiguous. No definitive surfaces. Choose a hypothesis explicitly to inspect an alternative.' : result.status === 'cancelled' ? 'Processing was cancelled. No derived geometry is displayed.' : 'No definitive surface mesh. Review diagnostics and measurement guidance.';
  const options = [new Option('Choose a surface', ''), ...current.map((surface, index) => new Option(`${index + 1} · ${surface.surface_id}`, String(index)))];
  $('#result-surface').replaceChildren(...options); $('#result-surface').disabled = !current.length;
  selectSurface('');
}
function show(value, name) {
  const valid = validateResult(value);
  // Validation completes before replacing the last usable result.
  const previous = result;
  result = valid;
  try { choose('definitive'); } catch (error) { result = previous; throw error; }
  $('#result-summary').hidden = false; $('#result-details').hidden = false;
  $('#result-status').textContent = `${valid.status.replaceAll('_', ' ')} · ${valid.surfaces.length} surfaces`;
  const classes = valid.provenance.evidence_classes;
  $('#result-provenance').textContent = Array.isArray(classes) && classes.length ? classes.map(label).join(' + ') : 'Not supplied';
  $('#result-revision').textContent = valid.stale === true ? 'STALE · reprocess before relying on this result' : valid.stale === false ? 'Current at export' : 'Freshness not supplied';
  $('#result-choice').replaceChildren(new Option('Backend surfaces · conditional', 'definitive'), ...(valid.hypotheses ?? []).map((hypothesis, index) => new Option(`Alternative ${index + 1} · ${hypothesis.hypothesis_id ?? 'unnamed'}`, String(index))));
  $('#result-choice').disabled = false;
  const identity = $('#result-identity'); identity.replaceChildren();
  pair(identity, 'File', name); pair(identity, 'Session', valid.session_id ?? 'Not supplied'); pair(identity, 'Result', valid.result_id ?? 'Not supplied');
  pair(identity, 'Coordinate frame', label(valid.acquisition?.coordinate_frame_id ?? 'Not supplied'));
  pair(identity, 'Geometry provenance', label(valid.provenance.geometry ?? 'Not supplied'));
  pair(identity, 'Example omissions', label(valid.example_metadata ?? 'None declared'));
  list($('#result-diagnostics'), valid.diagnostics ?? [], 'No diagnostics supplied.');
  list($('#result-guidance'), valid.guidance ?? [], 'No measurement guidance supplied.');
  const dimensions = Array.isArray(valid.dimensions) ? valid.dimensions.slice(0, 64) : [];
  list($('#result-dimensions'), dimensions.map(dimension => `${number(dimension.value_m)} m · standard deviation ${number(dimension.std_m, 5)} m · reference ${label(dimension.reference_point_m)} · direction ${label(dimension.direction)}`), 'No local separations supplied.');
  notice(`Loaded ${name}. Display checks cover the rendering contract; they do not authenticate recordings or establish scientific accuracy.`);
  for (const listener of resultListeners) listener(result);
}
async function loadText(text, name, version) {
  if (version !== loadVersion) return;
  if (new TextEncoder().encode(text).byteLength > MAX_RESULT_BYTES) throw new Error('Result exceeds the 32 MiB viewer limit.');
  show(JSON.parse(text), name);
}
$('#result-file').addEventListener('change', async event => {
  const version = ++loadVersion, file = event.target.files[0];
  if (!file) return;
  notice(`Reading ${file.name} locally…`);
  try {
    if (file.size > MAX_RESULT_BYTES) throw new Error('Result exceeds the 32 MiB viewer limit.');
    await loadText(await file.text(), file.name, version);
  } catch (error) { if (version === loadVersion) notice(`Could not open result: ${error.message}. ${result ? 'Previous result kept.' : 'No result loaded.'}`, true); }
  finally { event.target.value = ''; }
});
for (const button of document.querySelectorAll('[data-example]')) button.addEventListener('click', async () => {
  const version = ++loadVersion, name = button.dataset.example;
  notice(`Loading ${name} backend example…`);
  try {
    const response = await fetch(`./assets/results/${name}.json`, { signal: AbortSignal.timeout(10000) });
    if (!response.ok) throw new Error('Example unavailable; try opening a local result JSON.');
    await loadText(await response.text(), `${name}.json · bundled backend example`, version);
  } catch (error) { if (version === loadVersion) notice(`Could not open example: ${error.message}. ${result ? 'Previous result kept.' : ''}`, true); }
});
$('#result-choice').addEventListener('change', event => { try { choose(event.target.value); } catch (error) { notice(error.message, true); } });
$('#result-surface').addEventListener('change', event => selectSurface(event.target.value));
$('#result-fit').addEventListener('click', () => view?.fit());
$('#result-top').addEventListener('click', () => view?.fit(true));

// Only the opt-in same-origin workspace imports these controller entry points.
export function getDisplayVersion() { return loadVersion; }
export function getBackendResult() { return result; }
export function subscribeBackendResult(listener) { resultListeners.add(listener); return () => resultListeners.delete(listener); }
export function openBackendResult(value, name) { ++loadVersion; show(value, name); }
export function markSessionRevision(session) {
  if (result?.session_id === session.session_id && Number.isInteger(result.session_revision)) {
    result = { ...result, stale: result.session_revision !== session.revision };
    $('#result-revision').textContent = result.stale ? 'STALE · reprocess before relying on this result' : 'Current at session refresh';
    for (const listener of resultListeners) listener(result);
  }
}
