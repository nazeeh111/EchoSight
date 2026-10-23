/** Compare complete backend results through the existing local policy. No geometry fitting here. */
const MAX_COMPARE_BYTES = 65 * 1024 * 1024;
const named = result => typeof result?.result_id === 'string' && result.result_id.length > 0;
const finite = value => typeof value === 'number' && Number.isFinite(value);
const text = value => typeof value === 'string' ? value : 'Unavailable';

function validateComparison(value, previous, current) {
  if (!value || value.schema_version !== '1.1' || !['comparable', 'incomparable'].includes(value.status)
      || value.previous_result_id !== previous.result_id || value.current_result_id !== current.result_id
      || value.physical_scene_change_established !== false) throw new Error('Unexpected comparison response identity or semantics.');
  const previousIDs = new Set(previous.surfaces.map(surface => surface.surface_id));
  const currentIDs = new Set(current.surfaces.map(surface => surface.surface_id));
  for (const [key, ids] of [['newly_supported_surface_ids', currentIDs], ['unconfirmed_previous_surface_ids', previousIDs]]) {
    if (!Array.isArray(value[key]) || value[key].length > 64 || value[key].some(id => !ids.has(id))) throw new Error('Invalid comparison surface references.');
  }
  if (!Array.isArray(value.correspondences) || value.correspondences.length > 64 || value.correspondences.some(row =>
    !row || !previousIDs.has(row.previous_surface_id) || !currentIDs.has(row.current_surface_id)
    || !finite(row.normal_change_deg) || !finite(row.offset_change_m)
    || ![null, undefined].includes(row.additional_support_count) && (!Number.isInteger(row.additional_support_count) || row.additional_support_count < 0 || row.additional_support_count > 32))) throw new Error('Invalid comparison correspondences.');
  return value;
}

export function initComparison(document, client, { getResult, subscribe, download = saveJSON }) {
  const el = name => document.querySelector(`#comparison-${name}`);
  if (!el('panel')) return;
  const node = (tag, value) => { const element = document.createElement(tag); if (value !== undefined) element.textContent = value; return element; };
  let previous = null, carry = null, completed = null, pending = null, generation = 0;
  el('panel').hidden = false;
  const status = message => { el('status').textContent = message; };
  function controls() {
    const current = getResult();
    el('keep').disabled = !!pending || !named(current) || current.status === 'cancelled';
    el('run').disabled = !!pending || !previous || !named(current) || current === previous || current.status === 'cancelled';
    el('download').disabled = !completed;
  }
  function clear() {
    completed = null; el('output').hidden = true; el('output').replaceChildren();
  }
  function changed() {
    ++generation; pending?.abort(); pending = null; clear(); controls();
    status(previous ? 'Displayed result changed. Compare explicitly to update the change report.' : 'Keep the displayed result as the previous snapshot to begin.');
  }
  subscribe(changed);
  el('keep').addEventListener('click', () => {
    const current = getResult();
    if (pending || !named(current) || current.status === 'cancelled') return;
    // Carry only the verified comparison whose current snapshot is now anchored.
    carry = completed?.current === current && completed.value.status === 'comparable' ? completed.value : null;
    previous = current; ++generation; clear();
    el('previous').textContent = `Previous: ${current.result_id} · ${current.status} · ${current.surfaces.length} surfaces${current.stale ? ' · stale snapshot' : ''}. ${carry ? 'Display track labels carried from the previous comparison.' : 'Display track labels begin with this snapshot.'}`;
    status('Previous snapshot kept in page memory. Open or process the next result, then compare.'); controls();
  });
  function render(value, current) {
    const output = el('output'); output.replaceChildren(); output.hidden = false;
    output.append(node('p', `${value.previous_result_id} → ${value.current_result_id}. ${previous.status} → ${current.status}.${previous.stale || current.stale ? ' At least one snapshot is stale relative to its session.' : ''}`));
    if (value.status === 'incomparable') {
      output.append(node('p', 'These snapshots are incomparable. No geometry or support change is established.'));
      for (const diagnostic of (Array.isArray(value.diagnostics) ? value.diagnostics.slice(0, 32) : [])) output.append(node('p', typeof diagnostic === 'string' ? diagnostic : text(diagnostic?.message)));
      return;
    }
    const available = value.support_comparison_status === 'available';
    output.append(node('p', `${value.correspondences.length} corresponding patches · ${value.newly_supported_surface_ids.length} newly supported · ${value.unconfirmed_previous_surface_ids.length} previous patches unconfirmed. Recording support comparison: ${available ? 'available' : 'unavailable; session identity is missing'}.`));
    for (const [label, ids] of [['Newly supported', value.newly_supported_surface_ids], ['Previous, now unconfirmed', value.unconfirmed_previous_surface_ids]]) output.append(node('p', `${label}: ${ids.length ? ids.join(', ') : 'None'}.`));
    const scroll = node('div'); scroll.className = 'comparison-scroll';
    const table = node('table'), head = node('thead'), header = node('tr');
    for (const label of ['Previous → current patch', 'Normal change', 'Offset change at source', 'Additional recording support', 'Previous support not retained']) { const th = node('th', label); th.scope = 'col'; header.append(th); }
    head.append(header); table.append(head); const body = node('tbody');
    for (const row of value.correspondences) {
      const tr = node('tr');
      for (const label of [`${row.previous_surface_id} → ${row.current_surface_id}`, `${row.normal_change_deg.toFixed(3)}°`, `${(row.offset_change_m * 1000).toFixed(2)} mm`, available && Number.isInteger(row.additional_support_count) ? String(row.additional_support_count) : 'Unavailable', available && Array.isArray(row.lost_support_references) ? String(row.lost_support_references.length) : 'Unavailable']) tr.append(node('td', label));
      body.append(tr);
    }
    table.append(body); scroll.append(table); output.append(scroll);
    output.append(node('p', 'Offset is signed plane displacement at the shared source reference. Continuity gates are display choices, not significance tests or physical object identity. Missing echoes do not establish absence. The download retains track labels, scoped support references and exact comparison details.'));
  }
  el('run').addEventListener('click', async () => {
    const current = getResult();
    if (pending || !previous || !named(current) || current === previous || current.status === 'cancelled') return;
    clear(); const version = ++generation, controller = new AbortController(); pending = controller; controls();
    status('Comparing the two snapshots with the local backend…');
    try {
      const json = { previous, current, ...(carry ? { previous_comparison: carry } : {}) };
      if (new TextEncoder().encode(JSON.stringify(json)).byteLength > MAX_COMPARE_BYTES) throw new Error('Comparison exceeds the 65 MiB API limit. Use compact results or the CLI.');
      const value = await client.request('/v1/compare', { method: 'POST', json, signal: AbortSignal.any([controller.signal, AbortSignal.timeout(120000)]) });
      if (version !== generation || current !== getResult()) return;
      validateComparison(value, previous, current);
      render(value, current); completed = { value, current };
      status(value.status === 'comparable' ? 'Comparison complete. These are changes in inference and support; physical scene change is not established.' : 'Comparison complete: incompatible snapshots. Review the reason below.');
    } catch (error) {
      if (version === generation) { clear(); status(`Could not compare: ${error.message}. Both result snapshots remain available.`); }
    } finally { if (version === generation) { pending = null; controls(); } }
  });
  el('download').addEventListener('click', () => { if (completed) download(completed.value); });
  globalThis.addEventListener?.('pagehide', () => pending?.abort(), { once: true });
  controls();
  return { getState: () => ({ previous, carry, completed, pending: !!pending }) };
}

function saveJSON(value) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(value, null, 2)], { type: 'application/json' }));
  const link = document.createElement('a'); link.href = url; link.download = 'echosight-comparison.json'; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
