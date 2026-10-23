// Exercise actual scene methods and bundled Three.js without a browser/GPU.
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import vm from 'node:vm';
import test from 'node:test';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '../demo');
const modules = new Map();
async function source(path) {
  if (!modules.has(path)) modules.set(path, readFile(path, 'utf8').then(code =>
    new vm.SourceTextModule(code, { identifier: path })));
  return modules.get(path);
}
const scene = await source(resolve(root, 'scene.js'));
await scene.link(async (specifier, parent) => source(
  specifier === 'three' ? resolve(root, 'vendor/three.module.js') :
  specifier.startsWith('three/addons/') ? resolve(root, 'vendor/addons', specifier.slice(13)) :
  resolve(dirname(parent.identifier), specifier),
));
await scene.evaluate();
const { RoomView } = scene.namespace;
const THREE = (await modules.get(resolve(root, 'vendor/three.module.js'))).namespace;

function view() {
  const result = Object.create(RoomView.prototype);
  Object.assign(result, { nodes: new THREE.Group(), rayGroup: new THREE.Group(), replay: null });
  // Only labels need a browser canvas. Keep real textures and materials for disposal checks.
  result.label = () => new THREE.Sprite(new THREE.SpriteMaterial({ map: new THREE.Texture() }));
  result.makeNodes(3);
  return result;
}

test('replay keeps geometry and materials stable across 300 animation frames', () => {
  const room = view();
  const echoes = [{ angle: 0 }, { angle: 90 }, { angle: 180 }];
  room.setReplay(0, echoes, 0);
  const objects = [...room.rayGroup.children];
  const geometries = objects.map(object => object.geometry);
  const materials = objects.map(object => object.material);
  for (let frame = 0; frame < 300; frame++) room.setReplay(0, echoes, frame / 299);
  assert.deepEqual(room.rayGroup.children, objects);
  assert.deepEqual(objects.map(object => object.geometry), geometries);
  assert.deepEqual(objects.map(object => object.material), materials);
  room.setReplay(0, echoes, null);
  assert.ok(room.replay.paths.every(path => !path.marker.visible && path.line.material.opacity === .8));
  assert.equal(room.replay.paths[0].start.z, room.phonePositions[0].z - 4);
});

test('switching replay source disposes obsolete resources and clears hub rays', () => {
  const room = view(), echoes = [{ angle: 45 }];
  room.setReplay(0, echoes, .1);
  let disposed = 0;
  for (const object of room.rayGroup.children) {
    object.geometry.addEventListener('dispose', () => disposed++);
    object.material.addEventListener('dispose', () => disposed++);
  }
  room.setReplay(-1, [], null);
  assert.equal(disposed, 4);
  assert.equal(room.rayGroup.children.length, 0);
});

test('phone array replacement releases old geometry, materials and label textures', () => {
  const room = view();
  const resources = new Set();
  room.nodes.traverse(object => {
    if (object.geometry) resources.add(object.geometry);
    if (object.material) resources.add(object.material);
    if (object.material?.map) resources.add(object.material.map);
  });
  const disposed = new Set();
  for (const resource of resources) resource.addEventListener('dispose', () => disposed.add(resource));
  room.makeNodes(5);
  assert.equal(room.nodeObjects.length, 5);
  assert.deepEqual(disposed, resources);
});

test('object isolation cancels the previous camera transition and orbit', () => {
  const room = view();
  const bounds = new THREE.Box3(new THREE.Vector3(0, 0, 0), new THREE.Vector3(1, 2, 3));
  Object.assign(room, {
    groupMap: new Map([['chair', { bounds }]]), hidden: new Set(), isolated: null,
    cameraMove: { to: 'old preset' }, orbit: true, userCamera: false,
    camera: new THREE.PerspectiveCamera(), controls: { target: new THREE.Vector3() },
  });
  room.isolate('chair');
  assert.equal(room.cameraMove, null);
  assert.equal(room.orbit, false);
  assert.equal(room.userCamera, true);
  assert.ok(room.controls.target.equals(bounds.getCenter(new THREE.Vector3())));
});
