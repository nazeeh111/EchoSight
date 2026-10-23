import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { resolve, dirname } from 'node:path';
import vm from 'node:vm';
import test from 'node:test';
import { validateResult, displayedSurfaces, evidenceRows, displayText } from '../demo/result-data.js';
const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const fixture = async name => JSON.parse(await readFile(resolve(root, 'examples/frontend', `${name}.json`), 'utf8'));
const empty = status => ({ schema_version: '1.0', status, surfaces: [], hypotheses: [], diagnostics: [], provenance: { physical_validation: false } });
test('bundled examples match original backend outputs byte-for-byte and validate', async () => {
  for (const name of ['material-room', 'ambiguous', 'no-result']) {
    assert.deepEqual(await readFile(resolve(root, 'demo/assets/results', `${name}.json`)), await readFile(resolve(root, 'examples/frontend', `${name}.json`)));
    validateResult(await fixture(name));
  }
});
test('empty and cancelled outputs need no invented IDs or geometry', () => {
  for (const status of ['no_result', 'cancelled']) {
    const result = empty(status); result.session_id = null;
    assert.equal(validateResult(result), result); assert.deepEqual(displayedSurfaces(result).surfaces, []);
  }
});
test('ambiguous interpretations are explicit and never combined', async () => {
  const result = validateResult(await fixture('ambiguous'));
  assert.equal(displayedSurfaces(result).surfaces.length, 0);
  const choice = displayedSurfaces(result, '0');
  assert.equal(choice.alternative, true); assert.equal(choice.surfaces, result.hypotheses[0].surfaces);
  assert.throws(() => displayedSurfaces(result, '100'));
  assert.deepEqual(displayedSurfaces(result, '1').surfaces, []);
  assert.ok(result.hypotheses[1].planes.length > 0);
});
test('bare-plane hypotheses retain no invented support meshes', () => {
  const result = empty('ambiguous'); result.hypotheses.push({ planes: [{ normal: [0, 0, 1], offset_m: 2 }] });
  validateResult(result); assert.deepEqual(displayedSurfaces(result, '0').surfaces, []);
});
test('rejects contradictory status, invalid indices, nonfinite geometry and false extent claims', async () => {
  const base = await fixture('material-room');
  for (const mutate of [
    r => { r.status = 'ambiguous'; }, r => { r.status = 'cancelled'; },
    r => { r.surfaces[0].triangles[0][0] = 100000; }, r => { r.surfaces[0].vertices_m[0][2] = Infinity; },
    r => { r.surfaces[0].normal = [0, 0, 2]; }, r => { r.surfaces[0].extent_status = 'known'; },
    r => { r.surfaces[0].uncertainty.offset_std_m = -1; }, r => { r.surfaces[0].support[0].observed_delay_s = NaN; },
    r => { r.provenance.physical_validation = true; }, r => { r.surfaces[1].surface_id = r.surfaces[0].surface_id; },
    r => { r.dimensions = [null]; }, r => { r.interpretation.source_result_id = 'unrelated-result'; },
  ]) { const result = structuredClone(base); mutate(result); assert.throws(() => validateResult(result)); }
});
test('cancelled outputs retract interpretation, dimensions, guidance and derived fit claims', async () => {
  const base = await fixture('material-room');
  base.status = 'cancelled'; base.surfaces = []; base.hypotheses = [];
  for (const field of ['dimensions', 'guidance', 'interpretation', 'shared_image_source_covariance_m2', 'score']) {
    const result = empty('cancelled'); result[field] = base[field] ?? (field === 'guidance' ? ['move'] : []);
    if (field === 'guidance' && !result[field].length) result[field] = ['move'];
    assert.throws(() => validateResult(result));
  }
});
test('viewer resource budgets reject oversized meshes before rendering', async () => {
  const result = await fixture('material-room'); result.surfaces[0].vertices_m = Array.from({ length: 4097 }, () => [0, 0, 0]);
  assert.throws(() => validateResult(result), /4096/);
});
test('echo rows preserve IDs, signed residuals and supplied poses with exact ms conversion', async () => {
  const result = await fixture('material-room'), surface = result.surfaces[0], rows = evidenceRows(result, surface);
  assert.equal(rows[0].observed_ms, surface.support[0].observed_delay_s * 1000);
  assert.equal(rows[0].residual_ms, surface.support[0].residual_s * 1000);
  assert.equal(rows[0].source, result.acquisition.source_position_m);
  assert.equal(rows[0].receiver, result.acquisition.captures.find(c => c.capture_id === rows[0].capture_id).receiver_position_m);
  delete result.acquisition;
  assert.equal(evidenceRows(result, surface)[0].source, null); assert.equal(evidenceRows(result, surface)[0].receiver, null);
});
const modules = new Map();
async function source(path) {
  if (!modules.has(path)) modules.set(path, readFile(path, 'utf8').then(code => new vm.SourceTextModule(code, { identifier: path })));
  return modules.get(path);
}
const scene = await source(resolve(root, 'demo/result-view.js'));
await scene.link(async (specifier, parent) => source(specifier === 'three' ? resolve(root, 'demo/vendor/three.module.js') : specifier.startsWith('three/addons/') ? resolve(root, 'demo/vendor/addons', specifier.slice(13)) : resolve(dirname(parent.identifier), specifier)));
await scene.evaluate();
const { ResultView, releaseGroup } = scene.namespace;
const THREE = (await modules.get(resolve(root, 'demo/vendor/three.module.js'))).namespace;
function view() {
  const room = Object.create(ResultView.prototype);
  Object.assign(room, { group: new THREE.Group(), rays: new THREE.Group(), scene: new THREE.Scene(), meshes: [], fit() {}, requestRender() {} });
  room.scene.add(room.group, room.rays); return room;
}
test('actual vertices retain z-up coordinates and triangle topology; rays retain supplied endpoints', async () => {
  const result = validateResult(await fixture('material-room')), room = view(); room.setResult(result, result.surfaces, false);
  assert.equal(room.meshes.length, result.surfaces.length);
  const mesh = room.meshes[0], expected = result.surfaces[0];
  assert.deepEqual([...mesh.geometry.index.array], expected.triangles.flat());
  const positions = [...mesh.geometry.attributes.position.array];
  expected.vertices_m.flat().forEach((value, index) => assert.ok(Math.abs(positions[index] - value) < 1e-5));
  room.select(expected); const ray = room.rays.children.find(object => object.isLine);
  assert.equal(ray.geometry.attributes.position.count, 3);
  assert.ok(Math.abs(ray.geometry.attributes.position.getZ(0) - result.acquisition.source_position_m[2]) < 1e-5);
});
test('loading empty geometry clears obsolete meshes, rays and GPU resources', async () => {
  const result = await fixture('material-room'), room = view(); room.setResult(result, result.surfaces, false); room.select(result.surfaces[0]);
  let disposed = 0; room.group.traverse(object => object.geometry?.addEventListener('dispose', () => disposed++));
  room.setResult(empty('no_result'), [], false);
  assert.ok(disposed > 0); assert.equal(room.group.children.length, 0); assert.equal(room.rays.children.length, 0); assert.equal(room.meshes.length, 0);
});
test('missing poses draw reflection points without fabricated rays', async () => {
  const result = await fixture('material-room'), room = view(); delete result.acquisition;
  room.setResult(result, result.surfaces, false); room.select(result.surfaces[0]);
  assert.equal(room.rays.children.some(object => object.isLine), false); assert.equal(room.rays.children.length, result.surfaces[0].support.length);
  releaseGroup(room.rays); assert.equal(room.rays.children.length, 0);
});

test('deep imported metadata cannot throw during presentation and malformed diagnostics reject before commit', async () => {
  const deep = JSON.parse('['.repeat(12000) + '0' + ']'.repeat(12000));
  assert.equal(displayText(deep), 'Value is too deeply nested to display.');
  assert.equal(displayText('x'.repeat(3000)).length, 2000);
  const result = await fixture('material-room'); result.diagnostics = [deep];
  assert.throws(() => validateResult(result), /Diagnostics/);
  const original = await fixture('material-room');
  original.example_metadata = deep;
  validateResult(original);
  assert.doesNotThrow(() => displayText(original.example_metadata));
});
