/** Bounded display contract for backend v1.0 JSON. This is not scientific validation. */
export const MAX_RESULT_BYTES = 32 * 1024 * 1024;
const statuses = new Set(['ok', 'partial', 'ambiguous', 'no_result', 'cancelled']);
const object = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const finite = value => typeof value === 'number' && Number.isFinite(value);
const vector = value => Array.isArray(value) && value.length === 3 && value.every(n => finite(n) && Math.abs(n) <= 1e6);
const text = value => typeof value === 'string' && value.length > 0 && value.length <= 1000;
function require(condition, message) { if (!condition) throw new Error(message); }
function list(value, max, field) {
  require(Array.isArray(value) && value.length <= max, `${field} must be a bounded array (maximum ${max}).`);
  return value;
}
function surfaces(value, field, budget, allowDuplicateIds = false) {
  const ids = new Set();
  for (const surface of list(value, 64, field)) {
    require(object(surface) && text(surface.surface_id), `${field}: surface ID required.`);
    require(allowDuplicateIds || !ids.has(surface.surface_id), `${field}: duplicate surface ID.`); ids.add(surface.surface_id);
    require(vector(surface.normal) && Math.abs(Math.hypot(...surface.normal) - 1) < .001 && finite(surface.offset_m), 'Surface plane must have a finite offset and unit normal.');
    const vertices = list(surface.vertices_m, 4096, 'vertices_m');
    require(vertices.every(vector), 'Vertices must contain finite metre coordinates.');
    const triangles = list(surface.triangles, 8192, 'triangles');
    require(triangles.every(t => Array.isArray(t) && t.length === 3 && t.every(i => Number.isInteger(i) && i >= 0 && i < vertices.length)), 'Triangle indices must refer to supplied vertices.');
    budget.vertices += vertices.length; budget.triangles += triangles.length;
    require(budget.vertices <= 100000 && budget.triangles <= 200000, 'Result exceeds viewer geometry limits.');
    require(surface.extent_status === 'unknown', 'Surface extent must remain unknown.');
    require(object(surface.uncertainty) && finite(surface.uncertainty.offset_std_m) && surface.uncertainty.offset_std_m >= 0, 'Surface offset uncertainty must be a nonnegative finite number.');
    if (surface.uncertainty.normal_angular_std_rad != null)
      require(finite(surface.uncertainty.normal_angular_std_rad) && surface.uncertainty.normal_angular_std_rad >= 0, 'Normal uncertainty must be finite and nonnegative.');
    for (const support of list(surface.support, 32, 'support')) {
      require(object(support) && text(support.capture_id) && text(support.candidate_id) && vector(support.reflection_point_m), 'Surface support needs capture/candidate IDs and a finite reflection point.');
      require(['observed_delay_s', 'predicted_delay_s', 'residual_s'].every(key => finite(support[key])), 'Support delays and residuals must be finite seconds.');
    }
  }
}
export function validateResult(value) {
  require(object(value) && value.schema_version === '1.0' && statuses.has(value.status), 'Choose an EchoSight scene result with schema_version 1.0 and a recognized status.');
  require(value.session_id == null || text(value.session_id), 'Session ID must be a string or null.');
  require(value.result_id === undefined || text(value.result_id), 'Result ID must be a string when supplied.');
  require(object(value.provenance) && value.provenance.physical_validation === false, 'This viewer supports the unqualified v1.0 research contract (physical_validation: false).');
  const budget = { vertices: 0, triangles: 0 };
  surfaces(value.surfaces, 'surfaces', budget);
  if (['ambiguous', 'no_result', 'cancelled'].includes(value.status))
    require(value.surfaces.length === 0, `${value.status} cannot present definitive surfaces.`);
  const hypotheses = list(value.hypotheses ?? [], 32, 'hypotheses');
  if (value.status === 'cancelled') require(hypotheses.length === 0, 'Cancelled results cannot contain hypotheses.');
  for (const hypothesis of hypotheses) {
    require(object(hypothesis), 'Hypothesis must be an object.');
    require(hypothesis.hypothesis_id === undefined || text(hypothesis.hypothesis_id), 'Hypothesis ID must be a string when supplied.');
    if (hypothesis.image_sources_m !== undefined) require(list(hypothesis.image_sources_m, 64, 'image_sources_m').every(vector), 'Image sources must be finite positions.');
    if (hypothesis.planes !== undefined) for (const plane of list(hypothesis.planes, 64, 'planes'))
      require(object(plane) && vector(plane.normal) && Math.abs(Math.hypot(...plane.normal) - 1) < .001 && finite(plane.offset_m), 'Alternative planes need finite offsets and unit normals.');
    if (hypothesis.surfaces !== undefined) surfaces(hypothesis.surfaces, 'hypothesis surfaces', budget, true);
  }
  if (value.acquisition !== undefined) {
    require(object(value.acquisition), 'Acquisition must be an object.');
    if (value.acquisition.source_position_m != null) require(vector(value.acquisition.source_position_m), 'Source position must be a finite vector.');
    for (const capture of list(value.acquisition.captures ?? [], 32, 'captures')) {
      require(object(capture) && text(capture.capture_id), 'Capture ID required.');
      if (capture.receiver_position_m != null) require(vector(capture.receiver_position_m), 'Receiver position must be a finite vector.');
    }
  }
  for (const diagnostic of list(value.diagnostics ?? [], 512, 'diagnostics'))
    require(typeof diagnostic === 'string' || (object(diagnostic) && typeof diagnostic.code === 'string' && typeof diagnostic.message === 'string'), 'Diagnostics must be text or code/message objects.');
  const guidance = list(value.guidance ?? [], 128, 'guidance');
  const dimensions = list(value.dimensions ?? [], 64, 'dimensions');
  for (const dimension of dimensions) {
    require(object(dimension), 'Local separations must be objects.');
    for (const key of ['value_m', 'std_m']) if (dimension[key] !== undefined)
      require(finite(dimension[key]) && dimension[key] >= 0, 'Local separations and uncertainties must be nonnegative finite numbers.');
    for (const key of ['reference_point_m', 'direction']) if (dimension[key] !== undefined)
      require(vector(dimension[key]), 'Local separation reference and direction must be finite vectors.');
  }
  if (value.status === 'cancelled') {
    require(!dimensions.length && !guidance.length && value.interpretation === undefined, 'Cancelled results cannot retain dimensions, guidance or interpretation.');
    for (const field of ['shared_image_source_covariance_m2', 'higher_order_explanations', 'score'])
      require(value[field] === undefined, `Cancelled result retains ${field}.`);
  }
  if (value.interpretation !== undefined) {
    const interpretation = value.interpretation;
    require(object(interpretation) && interpretation.schema_version === '1.0' &&
      ['not_configured', 'no_geometry', 'complete', 'cancelled'].includes(interpretation.status), 'Interpretation must use the v1.0 contract.');
    require(text(value.result_id) && interpretation.source_result_id === value.result_id, 'Interpretation must be bound to this exact result ID.');
    const entries = list(interpretation.surface_interpretations, 64, 'surface_interpretations');
    const ids = new Set(), surfaces = new Set(value.surfaces.map(surface => surface.surface_id));
    for (const entry of entries) {
      require(object(entry) && surfaces.has(entry.surface_id) && !ids.has(entry.surface_id), 'Interpretation must identify a unique definitive surface.');
      ids.add(entry.surface_id);
      for (const key of ['material', 'appearance'])
        require(object(entry[key]) && ['estimated', 'unknown'].includes(entry[key].status), 'Material and appearance must declare estimated or unknown.');
    }
    if (interpretation.status !== 'complete') require(!entries.length, 'Incomplete interpretation cannot publish surface estimates.');
  }
  return value;
}
export function displayedSurfaces(result, choice = 'definitive') {
  if (choice === 'definitive') return { surfaces: result.surfaces, alternative: false, note: '' };
  const index = Number(choice);
  const hypothesis = Number.isInteger(index) ? result.hypotheses?.[index] : null;
  if (!hypothesis) throw new Error('Choose an available hypothesis.');
  return { surfaces: hypothesis.surfaces ?? [], alternative: true,
    note: typeof hypothesis.reason === 'string' ? hypothesis.reason : 'Alternative interpretation; not definitive structure.' };
}
export function evidenceRows(result, surface) {
  const captures = new Map((result.acquisition?.captures ?? []).map(capture => [capture.capture_id, capture]));
  return surface.support.map(support => ({ ...support,
    observed_ms: support.observed_delay_s * 1000,
    predicted_ms: support.predicted_delay_s * 1000,
    residual_ms: support.residual_s * 1000,
    receiver: captures.get(support.capture_id)?.receiver_position_m ?? null,
    source: result.acquisition?.source_position_m ?? null,
  }));
}

/** Imported metadata may be deeply nested. Display failure must never replace scene state. */
export function displayText(value, limit = 2000, pretty = false) {
  if (typeof value === 'string') return value.slice(0, limit);
  try { return JSON.stringify(value, null, pretty ? 2 : undefined)?.slice(0, limit) ?? 'Unavailable'; }
  catch { return 'Value is too deeply nested to display.'; }
}
