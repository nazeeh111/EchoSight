import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { evidenceRows } from './result-data.js';
export const PATCH_COLORS = [0xbcfa70, 0x67d7b3, 0x7cbbff, 0xe6b96e, 0xc7a1ff, 0xf2929b];
export function releaseGroup(group) {
  group.traverse(object => {
    object.geometry?.dispose();
    for (const material of [object.material].flat().filter(Boolean)) material.dispose();
  });
  group.clear();
}
export class ResultView {
  constructor(canvas, onPick) {
    this.canvas = canvas; this.onPick = onPick;
    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
    this.renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    this.renderer.setClearColor(0x080f0c, 1);
    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(48, 1, .01, 10000000);
    this.camera.up.set(0, 0, 1);
    this.controls = new OrbitControls(this.camera, canvas);
    this.controls.enableDamping = true;
    this.group = new THREE.Group(); this.scene.add(this.group);
    this.rays = new THREE.Group(); this.scene.add(this.rays);
    this.meshes = []; this.renderQueued = false;
    this.controls.addEventListener('change', () => this.requestRender());
    this.resizeObserver = new ResizeObserver(() => this.resize());
    this.resizeObserver.observe(canvas.parentElement);
    let down;
    canvas.addEventListener('pointerdown', event => { down = [event.clientX, event.clientY]; });
    canvas.addEventListener('pointercancel', () => { down = null; });
    canvas.addEventListener('pointerup', event => {
      if (!down || Math.hypot(event.clientX - down[0], event.clientY - down[1]) > 4) return;
      down = null;
      const bounds = canvas.getBoundingClientRect();
      const ray = new THREE.Raycaster();
      ray.setFromCamera(new THREE.Vector2(2 * (event.clientX - bounds.left) / bounds.width - 1, 1 - 2 * (event.clientY - bounds.top) / bounds.height), this.camera);
      const hit = ray.intersectObjects(this.meshes, false)[0];
      if (hit) onPick(hit.object.userData.surface);
    });
    this.resize();
  }
  requestRender() {
    if (this.renderQueued) return;
    this.renderQueued = true;
    requestAnimationFrame(() => {
      this.renderQueued = false;
      this.controls.update();
      this.renderer.render(this.scene, this.camera);
    });
  }
  resize() {
    const bounds = this.canvas.parentElement.getBoundingClientRect();
    if (!bounds.width || !bounds.height) return;
    this.renderer.setSize(bounds.width, bounds.height, false);
    this.camera.aspect = bounds.width / bounds.height; this.camera.updateProjectionMatrix();
    this.requestRender();
  }
  setResult(result, surfaces, alternative) {
    const group = new THREE.Group(), meshes = [];
    try {
      surfaces.forEach((surface, index) => {
        if (!surface.triangles.length) return;
        const geometry = new THREE.BufferGeometry();
        geometry.setAttribute('position', new THREE.Float32BufferAttribute(surface.vertices_m.flat(), 3));
        geometry.setIndex(surface.triangles.flat()); geometry.computeVertexNormals();
        const mesh = new THREE.Mesh(geometry, new THREE.MeshBasicMaterial({
          color: PATCH_COLORS[index % PATCH_COLORS.length], side: THREE.DoubleSide,
          transparent: true, opacity: alternative ? .3 : .6, depthWrite: false,
        }));
        mesh.userData.surface = surface; mesh.userData.opacity = alternative ? .3 : .6;
        group.add(mesh); meshes.push(mesh);
        const edges = new THREE.LineSegments(new THREE.EdgesGeometry(geometry), new THREE.LineBasicMaterial({ color: PATCH_COLORS[index % PATCH_COLORS.length] }));
        group.add(edges);
      });
    } catch (error) { releaseGroup(group); throw error; }
    releaseGroup(this.group); this.scene.remove(this.group);
    this.group = group; this.scene.add(group); this.meshes = meshes; this.result = result;
    releaseGroup(this.rays); this.fit();
  }
  fit(top = false) {
    const bounds = new THREE.Box3().setFromObject(this.group);
    if (bounds.isEmpty()) bounds.set(new THREE.Vector3(-1, -1, -1), new THREE.Vector3(1, 1, 1));
    const center = bounds.getCenter(new THREE.Vector3());
    const radius = Math.max(.1, bounds.getSize(new THREE.Vector3()).length() / 2);
    const angle = THREE.MathUtils.degToRad(this.camera.fov / 2);
    const distance = radius / Math.sin(Math.min(angle, Math.atan(Math.tan(angle) * this.camera.aspect))) * 1.2;
    this.camera.position.copy(center).add(new THREE.Vector3(top ? .0001 : 1, top ? 0 : -1.4, top ? 1 : 1).normalize().multiplyScalar(distance));
    this.controls.target.copy(center); this.controls.minDistance = radius * .05; this.controls.maxDistance = distance * 20;
    this.camera.near = Math.max(.0001, radius / 10000); this.camera.far = distance * 50;
    this.camera.updateProjectionMatrix(); this.controls.update(); this.requestRender();
  }
  select(surface) {
    releaseGroup(this.rays);
    for (const mesh of this.meshes) mesh.material.opacity = !surface || mesh.userData.surface === surface ? mesh.userData.opacity : .12;
    if (surface) {
      for (const row of evidenceRows(this.result, surface)) {
        const points = row.source && row.receiver ? [row.source, row.reflection_point_m, row.receiver] : [row.reflection_point_m];
        if (points.length > 1) this.rays.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(points.map(point => new THREE.Vector3(...point))), new THREE.LineBasicMaterial({ color: 0xffffff, transparent: true, opacity: .65 })));
        const dot = new THREE.Mesh(new THREE.SphereGeometry(.025, 8, 8), new THREE.MeshBasicMaterial({ color: 0xffffff }));
        dot.position.set(...row.reflection_point_m); this.rays.add(dot);
      }
    }
    this.requestRender();
  }
}
