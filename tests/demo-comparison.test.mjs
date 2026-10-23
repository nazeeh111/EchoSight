import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import vm from 'node:vm';
import test from 'node:test';
const code = await readFile(new URL('../demo/comparison.js', import.meta.url), 'utf8');
class Element {
  children = []; listeners = {}; disabled = false; hidden = false; ownText = '';
  set textContent(value) { this.ownText = String(value); this.children = []; }
  get textContent() { return this.ownText + this.children.map(child => child.textContent).join('\n'); }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.ownText = ''; this.children = children; }
  addEventListener(type, fn) { this.listeners[type] = fn; }
  fire(type = 'click') { return this.listeners[type]?.(); }
}
const result = (id, status = 'partial') => ({ result_id: id, status, surfaces: status === 'no_result' ? [] : [{ surface_id: `surface-${id}` }] });
function response(previous, current, changes = {}) {
  return { schema_version: '1.1', status: 'comparable', previous_result_id: previous.result_id, current_result_id: current.result_id,
    physical_scene_change_established: false, support_comparison_status: 'available', newly_supported_surface_ids: [], unconfirmed_previous_surface_ids: [],
    current_tracks: current.surfaces.map(surface => ({ surface_id: surface.surface_id, track_id: 'track-1' })),
    correspondences: previous.surfaces.length && current.surfaces.length ? [{ previous_surface_id: previous.surfaces[0].surface_id, current_surface_id: current.surfaces[0].surface_id, normal_change_deg: 0.012, offset_change_m: -0.003, additional_support_count: 2, lost_support_references: [{ session_id: "s", capture_id: "old" }] }] : [], ...changes };
}
async function fixture(handler = (_path, { json }) => response(json.previous, json.current)) {
  const nodes = new Map(), calls = [], downloads = []; let current, changed;
  const get = name => { if (!nodes.has(name)) nodes.set(name, new Element()); return nodes.get(name); };
  const document = { querySelector: selector => get(selector.replace('#comparison-', '')), createElement: () => new Element() };
  const context = vm.createContext({ TextEncoder, AbortController, AbortSignal });
  const module = new vm.SourceTextModule(code, { context }); await module.link(() => {}); await module.evaluate();
  const controller = module.namespace.initComparison(document, { request: async (path, options) => { calls.push({ path, ...options }); return handler(path, options); } },
    { getResult: () => current, subscribe: fn => { changed = fn; }, download: value => downloads.push(value) });
  const show = value => { current = value; changed(); };
  return { get, calls, downloads, show, ...controller };
}
test('comparison submits full snapshots to existing API, renders units and preserves exact download', async () => {
  const f = await fixture(), a = result('a'), b = result('b');
  assert.equal(f.get('keep').disabled, true); f.show(a); await f.get('keep').fire(); f.show(b); await f.get('run').fire();
  assert.equal(f.calls.length, 1); assert.equal(f.calls[0].path, '/v1/compare');
  assert.equal(f.calls[0].json.previous, a); assert.equal(f.calls[0].json.current, b);
  assert.match(f.get('output').textContent, /Previous support not retained/); assert.match(f.get('output').textContent, /-3.00 mm/); assert.match(f.get('output').textContent, /0.012°/);
  assert.match(f.get('output').textContent, /not significance tests/); assert.match(f.get('status').textContent, /physical scene change is not established/);
  await f.get('download').fire(); assert.equal(f.downloads[0], f.getState().completed.value);
});
test('late reply cannot replace report after a newer displayed result; request is aborted', async () => {
  let finish; const f = await fixture(() => new Promise(resolve => { finish = resolve; }));
  const a = result('a'), b = result('b'); f.show(a); await f.get('keep').fire(); f.show(b);
  const pending = f.get('run').fire(); f.show(result('c'));
  assert.equal(f.calls[0].signal.aborted, true); finish(response(a, b)); await pending;
  assert.equal(f.get('output').hidden, true); assert.equal(f.get('download').disabled, true); assert.equal(f.getState().previous, a);
});
test('keeping compared current snapshot carries backend track identities into the next comparison', async () => {
  const f = await fixture(), a = result('a'), b = result('b'), c = result('c');
  f.show(a); await f.get('keep').fire(); f.show(b); await f.get('run').fire(); const first = f.getState().completed.value;
  await f.get('keep').fire(); assert.equal(f.getState().carry, first); f.show(c); await f.get('run').fire();
  assert.equal(f.calls[1].json.previous_comparison, first); assert.equal(f.calls[1].json.previous, b);
});
test('calibration mismatch renders incomparable with no apparent movement table', async () => {
  const f = await fixture((_path, { json }) => response(json.previous, json.current, { status: 'incomparable', correspondences: [], diagnostics: [{ message: 'Use the same surveyed frame.' }] }));
  f.show(result('a')); await f.get('keep').fire(); f.show(result('b')); await f.get('run').fire();
  assert.match(f.get('output').textContent, /incomparable/); assert.match(f.get('output').textContent, /same surveyed frame/);
  assert.doesNotMatch(f.get('output').textContent, /Normal change/);
  await f.get('keep').fire(); assert.equal(f.getState().carry, null);
});
test('request failure, wrong identity and malformed rows preserve snapshots without publishing', async () => {
  for (const handler of [() => { throw new Error('Disconnected'); }, (_p, { json }) => response(json.previous, json.current, { current_result_id: 'other' }), (_p, { json }) => response(json.previous, json.current, { correspondences: [{ normal_change_deg: '0' }] })]) {
    const f = await fixture(handler), a = result('a'), b = result('b'); f.show(a); await f.get('keep').fire(); f.show(b); await f.get('run').fire();
    assert.equal(f.getState().previous, a); assert.equal(f.getState().completed, null); assert.equal(f.get('download').disabled, true);
    assert.match(f.get('status').textContent, /Both result snapshots remain available/); assert.equal(f.get('run').disabled, false);
  }
});
test('missing scope, no-result and stale states retain qualified interpretation', async () => {
  const f = await fixture((_p, { json }) => response(json.previous, json.current, { support_comparison_status: 'unavailable', newly_supported_surface_ids: [], unconfirmed_previous_surface_ids: ['surface-a'] }));
  f.show(result('a')); await f.get('keep').fire(); f.show({ ...result('b', 'no_result'), stale: true }); await f.get('run').fire();
  assert.match(f.get('output').textContent, /session identity is missing/); assert.match(f.get('output').textContent, /stale/);
  assert.match(f.get('output').textContent, /now unconfirmed: surface-a/); assert.match(f.get('output').textContent, /Missing echoes do not establish absence/);
});
test('cancelled or unnamed snapshots cannot start a comparison', async () => {
  const f = await fixture(); f.show(result('a')); await f.get('keep').fire();
  for (const value of [result('b', 'cancelled'), { status: 'partial', surfaces: [] }]) { f.show(value); await f.get('run').fire(); assert.equal(f.get('run').disabled, true); }
  assert.equal(f.calls.length, 0);
});
