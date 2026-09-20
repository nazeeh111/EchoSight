import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { clamp, smooth, seeded } from "./data.js";

const CENTER = new THREE.Vector3(6.875, 1.7, -5.4),
  OVERVIEW = new THREE.Vector3(22, 20, 14);
export class RoomView {
  constructor(canvas, onPick) {
    this.canvas = canvas;
    this.onPick = onPick;
    this.ready = false;
    this.mode = "scan";
    this.t = 0;
    this.blend = 1;
    this.nodesEnabled = true;
    this.motion = true;
    this.orbit = false;
    this.groupMap = new Map();
    this.hidden = new Set();
    this.isolated = null;
    this.selected = null;
    this.preset = "3d";
    this.phoneCount = 3;
    this.replay = null;
    this.userCamera = false;
    this.renderer = new THREE.WebGLRenderer({
      canvas,
      antialias: true,
      alpha: true,
      powerPreference: "high-performance",
      preserveDrawingBuffer: true,
    });
    this.renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    this.renderer.setClearColor(0x080f0c, 0);
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 0.92;
    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(44, 1, 0.05, 200);
    this.camera.position.copy(OVERVIEW);
    this.scene.add(this.camera);
    this.controls = new OrbitControls(this.camera, canvas);
    this.controls.target.copy(CENTER);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.085;
    this.controls.minDistance = 0.8;
    this.controls.maxDistance = 65;
    this.controls.maxPolarAngle = Math.PI * 0.96;
    this.controls.autoRotateSpeed = 0.45;
    this.controls.addEventListener("start", () => {
      this.userCamera = true;
    });
    this.scene.add(new THREE.HemisphereLight(0xf7ffe9, 0x667e81, 1.55));
    const key = new THREE.DirectionalLight(0xfff6e4, 1.6);
    key.position.set(5, 15, 5);
    this.scene.add(key);
    const fill = new THREE.DirectionalLight(0xe8f3ff, 0.65);
    fill.position.set(12, 5, -8);
    this.scene.add(fill);
    const interior = new THREE.PointLight(0xffffff, 20, 22, 1.5);
    interior.position.set(6.87, 4, -5.2);
    this.scene.add(interior);
    this.grid = new THREE.GridHelper(30, 30, 0x3d6035, 0x203a2a);
    this.grid.position.set(6.875, -0.2, -5.4);
    this.grid.material.transparent = true;
    this.grid.material.opacity = 0.45;
    this.scene.add(this.grid);
    this.nodes = new THREE.Group();
    this.scene.add(this.nodes);
    this.rings = [];
    for (let i = 0; i < 5; i++) {
      const ring = new THREE.Mesh(
        new THREE.RingGeometry(1, 1.028, 100),
        new THREE.MeshBasicMaterial({
          color: 0xbcfa70,
          transparent: true,
          opacity: 0.4,
          side: THREE.DoubleSide,
          depthWrite: false,
        }),
      );
      ring.rotation.x = -Math.PI / 2;
      ring.position.set(6.875, 0.2, -5.4);
      this.scene.add(ring);
      this.rings.push(ring);
    }
    this.rayGroup = new THREE.Group();
    this.scene.add(this.rayGroup);
    this.makeNodes(3);
    this.makeDimensions();
    this.box = new THREE.BoxHelper(
      new THREE.Mesh(new THREE.BoxGeometry(0.1, 0.1, 0.1)),
      0xbcfa70,
    );
    this.box.material.transparent = true;
    this.box.material.opacity = 0.8;
    this.box.visible = false;
    this.scene.add(this.box);
    let down;
    canvas.addEventListener(
      "pointerdown",
      (e) => (down = [e.clientX, e.clientY]),
    );
    canvas.addEventListener("pointerup", (e) => {
      if (
        !down ||
        Math.hypot(e.clientX - down[0], e.clientY - down[1]) > 4 ||
        this.mode !== "explore"
      )
        return;
      const rect = canvas.getBoundingClientRect(),
        mouse = new THREE.Vector2(
          ((e.clientX - rect.left) / rect.width) * 2 - 1,
          (-(e.clientY - rect.top) / rect.height) * 2 + 1,
        );
      const ray = new THREE.Raycaster();
      ray.setFromCamera(mouse, this.camera);
      const hits = ray
        .intersectObjects(this.meshes || [], false)
        .filter(
          (h) =>
            h.object.visible &&
            h.object.userData.object_id &&
            !/ceiling/i.test(h.object.userData.category || ""),
        );
      if (hits[0]) this.onPick(hits[0].object.userData.object_id);
    });
    new ResizeObserver(() => this.resize()).observe(canvas.parentElement);
    this.resize();
  }
  resize() {
    const r = this.canvas.parentElement.getBoundingClientRect();
    if (!r.width || !r.height) return;
    this.renderer.setSize(r.width, r.height, false);
    this.camera.aspect = r.width / r.height;
    this.camera.updateProjectionMatrix();
  }
  async load() {
    const gltf = await new GLTFLoader().loadAsync(
      "./assets/room-corrected.glb",
    );
    this.model = gltf.scene;
    this.model.updateMatrixWorld(true);
    this.meshes = [];
    this.model.traverse((m) => {
      if (!m.isMesh) return;
      this.meshes.push(m);
      m.userData.isStructure = ["Walls", "Floor", "Ceiling", "Doors"].includes(
        m.userData.category,
      );
      m.userData.originalMaterial = m.material;
      const original = m.material;
      const list = Array.isArray(original) ? original : [original];
      const fades = list.map((mat) => {
        const x = mat.clone();
        x.transparent = true;
        x.depthWrite = !mat.transparent;
        x.userData.originalOpacity = mat.opacity;
        x.userData.originalColor = mat.color.clone();
        x.userData.originalRoughness = mat.roughness;
        x.userData.originalMetalness = mat.metalness;
        return x;
      });
      m.userData.fadeMaterial = Array.isArray(original) ? fades : fades[0];
      const id = m.userData.object_id || m.name;
      if (!this.groupMap.has(id))
        this.groupMap.set(id, {
          id,
          name: m.userData.name || id,
          meta: m.userData,
          meshes: [],
          bounds: new THREE.Box3(),
        });
      const group = this.groupMap.get(id);
      group.meshes.push(m);
      group.bounds.union(new THREE.Box3().setFromObject(m));
    });
    this.groups = [...this.groupMap.values()];
    this.meshes.forEach((m) => {
      const g = this.groupMap.get(m.userData.object_id || m.name);
      m.userData.buildOrder =
        clamp((-g.bounds.getCenter(new THREE.Vector3()).z - 1) / 10) * 0.72;
    });
    this.scene.add(this.model);
    this.makeEvidence();
    this.makeLasers();
    this.ready = true;
    this.render(8, "scan", 0);
    this.render(13, "scan", 0);
    this.render(19, "scan", 0);
    this.render(26, "scan", 0);
    this.render(27, "explore", 0);
    this.setPreset("3d", true);
    this.mode = "welcome";
    this.model.visible = false;
    this.points.visible = false;
    this.edges.visible = false;
    this.lasers.visible = false;
    this.lastTime = undefined;
    return this.groups;
  }
  makeEvidence() {
    const r = seeded(8472),
      triangles = [[], []],
      edgePositions = [[], []];
    const a = new THREE.Vector3(),
      b = new THREE.Vector3(),
      c = new THREE.Vector3();
    this.meshes.forEach((m) => {
      const kind = m.userData.isStructure ? 0 : 1,
        p = m.geometry.attributes.position,
        ix = m.geometry.index;
      for (let i = 0; i < (ix ? ix.count : p.count); i += 3) {
        a.fromBufferAttribute(p, ix ? ix.getX(i) : i).applyMatrix4(
          m.matrixWorld,
        );
        b.fromBufferAttribute(p, ix ? ix.getX(i + 1) : i + 1).applyMatrix4(
          m.matrixWorld,
        );
        c.fromBufferAttribute(p, ix ? ix.getX(i + 2) : i + 2).applyMatrix4(
          m.matrixWorld,
        );
        triangles[kind].push([a.clone(), b.clone(), c.clone()]);
      }
      const eg = new THREE.EdgesGeometry(m.geometry, 35);
      eg.applyMatrix4(m.matrixWorld);
      edgePositions[kind].push(...eg.attributes.position.array);
      eg.dispose();
    });
    const n = 32000,
      pos = new Float32Array(n * 3),
      kinds = new Float32Array(n),
      seeds = new Float32Array(n),
      ranks = new Float32Array(n);
    for (let i = 0; i < n; i++) {
      const kind = i < 11500 ? 0 : 1,
        arr = triangles[kind],
        tri = arr[Math.floor(r() * arr.length)],
        u = Math.sqrt(r()),
        v = r();
      a.copy(tri[0])
        .multiplyScalar(1 - u)
        .addScaledVector(tri[1], u * (1 - v))
        .addScaledVector(tri[2], u * v);
      pos.set(a.toArray(), i * 3);
      kinds[i] = kind;
      seeds[i] = r();
      ranks[i] =
        kind === 0
          ? clamp(a.y / 4.9) * 0.55 + clamp(a.x / 14) * 0.2 + seeds[i] * 0.15
          : clamp((-a.z - 1) / 10) * 0.72 + seeds[i] * 0.15;
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(pos, 3));
    g.setAttribute("aKind", new THREE.BufferAttribute(kinds, 1));
    g.setAttribute("aSeed", new THREE.BufferAttribute(seeds, 1));
    g.setAttribute("aRank", new THREE.BufferAttribute(ranks, 1));
    this.pointMat = new THREE.ShaderMaterial({
      transparent: true,
      depthWrite: false,
      uniforms: {
        uWall: { value: 0 },
        uObject: { value: 0 },
        uWallFade: { value: 1 },
        uObjectFade: { value: 1 },
        uOpacity: { value: 1 },
        uTime: { value: 0 },
        uPixel: { value: Math.min(devicePixelRatio, 2) },
      },
      vertexShader: `attribute float aKind,aSeed,aRank; uniform float uWall,uObject,uTime,uPixel,uWallFade,uObjectFade; varying float vSeed,vAlpha; void main(){vSeed=aSeed;float progress=mix(uWall,uObject,aKind);float reveal=smoothstep(aRank-.04,aRank+.055,progress)*step(.00001,progress);vAlpha=reveal*mix(uWallFade,uObjectFade,aKind);vec3 p=position; p.y+=(1.-reveal)*.35;vec4 mv=modelViewMatrix*vec4(p,1.);gl_Position=projectionMatrix*mv;gl_PointSize=clamp(47./-mv.z,1.25,3.4)*uPixel;}`,
      fragmentShader: `uniform float uOpacity;varying float vSeed,vAlpha;void main(){if(vAlpha<.015)discard;vec2 p=abs(gl_PointCoord-.5);if(max(p.x,p.y)>.43)discard;vec3 c=mix(vec3(.26,.81,.68),vec3(.76,.99,.46),step(.8,vSeed));gl_FragColor=vec4(c,vAlpha*uOpacity);}`,
    });
    this.points = new THREE.Points(g, this.pointMat);
    this.scene.add(this.points);
    this.edges = new THREE.Group();
    this.edgeParts = edgePositions.map((arr) => {
      const eg = new THREE.BufferGeometry();
      eg.setAttribute("position", new THREE.Float32BufferAttribute(arr, 3));
      const line = new THREE.LineSegments(
        eg,
        new THREE.LineBasicMaterial({
          color: 0xa4d775,
          transparent: true,
          opacity: 0,
          depthWrite: false,
        }),
      );
      this.edges.add(line);
      return line;
    });
    this.scene.add(this.edges);
  }
  makeLasers() {
    this.lasers = new THREE.Group();
    this.beams = [];
    for (let i = 0; i < 3; i++) {
      const geo = new THREE.BufferGeometry();
      geo.setAttribute(
        "position",
        new THREE.Float32BufferAttribute(new Float32Array(6), 3),
      );
      const core = new THREE.Line(
        geo,
        new THREE.LineBasicMaterial({
          color: 0xcaff84,
          transparent: true,
          opacity: 0.9,
          depthWrite: false,
          blending: THREE.AdditiveBlending,
        }),
      );
      const glow = new THREE.Mesh(
        new THREE.CylinderGeometry(0.048, 0.032, 1, 8),
        new THREE.MeshBasicMaterial({
          color: 0x6cf1bc,
          transparent: true,
          opacity: 0.16,
          depthWrite: false,
          blending: THREE.AdditiveBlending,
        }),
      );
      const outline = new THREE.Mesh(
        new THREE.CylinderGeometry(0.083, 0.07, 1, 8),
        new THREE.MeshBasicMaterial({
          color: 0x07100b,
          transparent: true,
          opacity: 0.85,
          depthTest: false,
          depthWrite: false,
        }),
      );
      outline.renderOrder = 5;
      outline.frustumCulled = false;
      const pg = new THREE.BufferGeometry();
      pg.setAttribute(
        "position",
        new THREE.Float32BufferAttribute(new Float32Array(64 * 3), 3),
      );
      const pixels = new THREE.Points(
        pg,
        new THREE.PointsMaterial({
          color: 0xc3ff7a,
          size: 0.072,
          transparent: true,
          opacity: 0.95,
          depthWrite: false,
          blending: THREE.AdditiveBlending,
        }),
      );
      const tip = new THREE.Mesh(
        new THREE.IcosahedronGeometry(0.085, 0),
        new THREE.MeshBasicMaterial({
          color: 0xe1ffbd,
          transparent: true,
          opacity: 0.95,
        }),
      );
      const ring = new THREE.Mesh(
        new THREE.RingGeometry(0.15, 0.18, 40),
        new THREE.MeshBasicMaterial({
          color: 0xaef577,
          transparent: true,
          opacity: 0.5,
          side: THREE.DoubleSide,
          depthWrite: false,
        }),
      );
      ring.rotation.x = -Math.PI / 2;
      [core, glow, pixels, tip, ring].forEach((part) => {
        part.material.depthTest = false;
        part.material.depthWrite = false;
        part.material.toneMapped = false;
        part.renderOrder = 6;
      });
      core.frustumCulled = false;
      pixels.frustumCulled = false;
      glow.frustumCulled = false;
      this.lasers.add(outline, core, glow, pixels, tip, ring);
      this.beams.push({ core, glow, pixels, tip, ring, outline });
    }
    this.scene.add(this.lasers);
  }
  updateLasers(t, clock, mode) {
    if (!this.lasers) return;
    const show = mode === "scan" && t >= 11.9 && t < 25;
    this.lasers.visible = show;
    if (!show) return;
    const fade = smooth((t - 11.9) / 0.5) * (1 - smooth((t - 24.1) / 0.9)),
      phase = t < 16 ? 0 : t < 20.5 ? 1 : 2,
      p =
        phase === 0
          ? clamp((t - 12) / 4)
          : phase === 1
            ? clamp((t - 16) / 4.5)
            : clamp((t - 20.5) / 4),
      up = new THREE.Vector3(0, 1, 0);
    this.beams.forEach((beam, i) => {
      const from = this.phonePositions[i]
        .clone()
        .add(new THREE.Vector3(0, 0.38, 0));
      let target;
      if (phase === 0) {
        const row = clamp(p * 1.15),
          sweep =
            (Math.sin((this.motion ? p * 2.7 : 0.8) * Math.PI + i * 1.8) + 1) /
            2;
        target =
          i === 0
            ? new THREE.Vector3(0.1, Math.max(0.1, row * 4.6), -sweep * 9.7)
            : i === 1
              ? new THREE.Vector3(13.65, Math.max(0.1, row * 4.6), -sweep * 9.7)
              : new THREE.Vector3(sweep * 13.5, 0.15 + row * 4.4, -9.65);
      } else if (phase === 1) {
        const xs = [1.65, 6.9, 11.35];
        target = new THREE.Vector3(
          xs[i] + Math.sin(p * Math.PI * 5 + i) * 0.65,
          0.72 + p * 1.1,
          -1.9 - p * 7.5,
        );
      } else {
        const sweep =
          (Math.sin((this.motion ? clock * 0.9 : 1) + i * 2) + 1) / 2;
        target = new THREE.Vector3(
          1 + sweep * 11.5,
          1.1 + p * 0.9,
          -2 - i * 2.6,
        );
      }
      const arr = beam.core.geometry.attributes.position;
      arr.setXYZ(0, from.x, from.y, from.z);
      arr.setXYZ(1, target.x, target.y, target.z);
      arr.needsUpdate = true;
      beam.core.material.opacity = fade * 0.85;
      const delta = target.clone().sub(from),
        length = delta.length();
      beam.glow.position.copy(from).addScaledVector(delta, 0.5);
      beam.glow.quaternion.setFromUnitVectors(up, delta.clone().normalize());
      beam.glow.scale.set(1, length, 1);
      beam.glow.material.opacity = fade * 0.65;
      beam.outline.position.copy(beam.glow.position);
      beam.outline.quaternion.copy(beam.glow.quaternion);
      beam.outline.scale.copy(beam.glow.scale);
      beam.outline.material.opacity = fade * 0.86;
      const pp = beam.pixels.geometry.attributes.position;
      for (let j = 0; j < 64; j++) {
        const q = (j / 64 + (this.motion ? clock * 0.75 : 0)) % 1,
          v = from.clone().addScaledVector(delta, q);
        pp.setXYZ(j, v.x, v.y, v.z);
      }
      pp.needsUpdate = true;
      beam.pixels.material.opacity = fade * 0.82;
      beam.tip.position.copy(target);
      beam.tip.material.opacity = fade;
      beam.ring.position.copy(target);
      beam.ring.material.opacity = fade * 0.5;
      beam.ring.scale.setScalar(
        1 + (this.motion ? Math.sin(clock * 3 + i) * 0.16 : 0),
      );
    });
  }
  label(text, color = "#bcfa70") {
    const cv = document.createElement("canvas");
    cv.width = 256;
    cv.height = 64;
    const ctx = cv.getContext("2d");
    ctx.fillStyle = "rgba(8,15,12,.86)";
    ctx.fillRect(0, 0, 256, 64);
    ctx.strokeStyle = "#314a32";
    ctx.strokeRect(1, 1, 254, 62);
    ctx.font = "25px monospace";
    ctx.fillStyle = color;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(text, 128, 33);
    const tex = new THREE.CanvasTexture(cv),
      s = new THREE.Sprite(
        new THREE.SpriteMaterial({
          map: tex,
          transparent: true,
          depthTest: false,
        }),
      );
    s.scale.set(1.5, 0.375, 1);
    s.renderOrder = 4;
    return s;
  }
  makeNodes(count) {
    this.phoneCount = count;
    this.nodes.clear();
    this.phonePositions = [
      [1.8, 0.9, -2.5],
      [12, 0.9, -3.5],
      [8.8, 0.9, -8.1],
      [2.2, 0.9, -8],
      [7, 0.9, -5.5],
    ].map((p) => new THREE.Vector3(...p));
    this.nodeObjects = [];
    this.phonePositions.slice(0, count).forEach((p, i) => {
      const group = new THREE.Group();
      group.position.copy(p);
      const body = new THREE.Mesh(
        new THREE.BoxGeometry(0.24, 0.48, 0.035),
        new THREE.MeshBasicMaterial({ color: 0x223521 }),
      );
      body.position.y = 0.1;
      group.add(body);
      const edge = new THREE.LineSegments(
        new THREE.EdgesGeometry(body.geometry),
        new THREE.LineBasicMaterial({ color: 0xbcfa70 }),
      );
      edge.position.y = 0.1;
      group.add(edge);
      const label = this.label("N0" + (i + 1));
      label.position.y = 0.68;
      label.scale.multiplyScalar(0.8);
      group.add(label);
      const halo = new THREE.Mesh(
        new THREE.RingGeometry(0.33, 0.35, 48),
        new THREE.MeshBasicMaterial({
          color: 0xbcfa70,
          side: THREE.DoubleSide,
          transparent: true,
          opacity: 0.55,
          depthWrite: false,
        }),
      );
      halo.rotation.x = -Math.PI / 2;
      halo.position.y = -0.24;
      group.add(halo);
      const line = new THREE.Line(
        new THREE.BufferGeometry().setFromPoints([
          new THREE.Vector3(6.875, 0.65, -5.4).sub(p),
          new THREE.Vector3(0, 0, 0),
        ]),
        new THREE.LineBasicMaterial({
          color: 0x53703e,
          transparent: true,
          opacity: 0.7,
        }),
      );
      group.add(line);
      this.nodes.add(group);
      this.nodeObjects.push(group);
    });
    const hub = new THREE.Group();
    hub.position.set(6.875, 0.65, -5.4);
    const screen = new THREE.Mesh(
      new THREE.BoxGeometry(0.85, 0.56, 0.04),
      new THREE.MeshBasicMaterial({ color: 0x416332 }),
    );
    hub.add(screen);
    const e = new THREE.LineSegments(
      new THREE.EdgesGeometry(screen.geometry),
      new THREE.LineBasicMaterial({ color: 0xbcfa70 }),
    );
    hub.add(e);
    const base = new THREE.Mesh(
      new THREE.BoxGeometry(0.9, 0.04, 0.45),
      new THREE.MeshBasicMaterial({ color: 0x66884a }),
    );
    base.position.set(0, -0.3, 0.2);
    hub.add(base);
    const label = this.label("HUB");
    label.position.y = 0.7;
    label.scale.multiplyScalar(0.8);
    hub.add(label);
    this.nodes.add(hub);
  }
  makeDimensions() {
    this.dimensions = new THREE.Group();
    this.dimensions.visible = false;
    const a = this.label("14.11 m");
    a.position.set(6.875, 0.1, 1.3);
    const b = this.label("11.15 m");
    b.position.set(15.1, 0.1, -5.4);
    const c = this.label("4.91 m");
    c.position.set(-1, 2.4, -1);
    this.dimensions.add(a, b, c);
    this.scene.add(this.dimensions);
  }
  setPreset(name, instant = false) {
    this.preset = name;
    this.userCamera = false;
    const dest = {
      "3d": { pos: OVERVIEW, target: CENTER, fov: 44 },
      top: {
        pos: new THREE.Vector3(6.875, 26, -5.39),
        target: CENTER,
        fov: 44,
      },
      front: {
        pos: new THREE.Vector3(6.875, 3.8, -9.35),
        target: new THREE.Vector3(6.875, 1.7, -2.2),
        fov: 78,
      },
      source: {
        pos: new THREE.Vector3(6.875, 3.35, -1.35),
        target: new THREE.Vector3(6.875, 1.2, -5.4),
        fov: 44,
      },
    }[name] || { pos: OVERVIEW, target: CENTER, fov: 44 };
    if (instant) {
      this.camera.position.copy(dest.pos);
      this.controls.target.copy(dest.target);
      this.camera.fov = dest.fov;
      this.camera.updateProjectionMatrix();
      this.cameraMove = null;
    } else
      this.cameraMove = {
        from: this.camera.position.clone(),
        to: dest.pos.clone(),
        targetFrom: this.controls.target.clone(),
        targetTo: dest.target.clone(),
        fovFrom: this.camera.fov,
        fovTo: dest.fov,
        at: performance.now(),
        duration: this.motion ? 1000 : 0,
      };
    this.orbit = false;
    this.controls.autoRotate = false;
  }
  select(id) {
    this.selected = id;
    const group = this.groupMap.get(id);
    if (!group) {
      this.box.visible = false;
      return;
    }
    this.box.box = null;
    const box = group.bounds,
      min = box.min,
      max = box.max;
    const points = [
      new THREE.Vector3(min.x, min.y, min.z),
      new THREE.Vector3(max.x, min.y, min.z),
      new THREE.Vector3(max.x, max.y, min.z),
      new THREE.Vector3(min.x, max.y, min.z),
      new THREE.Vector3(min.x, min.y, max.z),
      new THREE.Vector3(max.x, min.y, max.z),
      new THREE.Vector3(max.x, max.y, max.z),
      new THREE.Vector3(min.x, max.y, max.z),
    ];
    const indices = [
      0, 1, 1, 2, 2, 3, 3, 0, 4, 5, 5, 6, 6, 7, 7, 4, 0, 4, 1, 5, 2, 6, 3, 7,
    ];
    const arr = [];
    indices.forEach((i) => arr.push(...points[i].toArray()));
    this.box.geometry.dispose();
    this.box.geometry = new THREE.BufferGeometry();
    this.box.geometry.setAttribute(
      "position",
      new THREE.Float32BufferAttribute(arr, 3),
    );
    this.box.geometry.computeBoundingSphere();
    this.box.visible = !this.hidden.has(id);
  }
  visibility() {
    this.meshes?.forEach((m) => {
      const id = m.userData.object_id || m.name;
      m.visible =
        !this.hidden.has(id) && (!this.isolated || id === this.isolated);
    });
    if (this.selected) this.box.visible = !this.hidden.has(this.selected);
  }
  isolate(id) {
    this.isolated = this.isolated === id ? null : id;
    this.visibility();
    if (this.isolated) {
      const b = this.groupMap.get(id).bounds,
        s = b.getSize(new THREE.Vector3()).length();
      const center = b.getCenter(new THREE.Vector3());
      this.camera.position
        .copy(center)
        .add(new THREE.Vector3(0.7, 0.65, 0.9).multiplyScalar(Math.max(s, 2)));
      this.controls.target.copy(center);
      this.camera.fov = 44;
      this.camera.updateProjectionMatrix();
    } else this.setPreset("front");
  }
  setReplay(phone, echoes, progress) {
    this.rayGroup.traverse((o) => {
      o.geometry?.dispose();
      if (o.material) o.material.dispose();
    });
    this.rayGroup.clear();
    if (phone < 0 || !this.phonePositions[phone]) return;
    const center = this.phonePositions[phone];
    echoes.forEach((echo, i) => {
      const a = (echo.angle * Math.PI) / 180,
        start = center
          .clone()
          .add(new THREE.Vector3(Math.sin(a) * 4, 0, -Math.cos(a) * 4)),
        end = center.clone();
      const active =
        progress === null || Math.abs(progress - i / echoes.length) < 0.13;
      const line = new THREE.Line(
        new THREE.BufferGeometry().setFromPoints([start, end]),
        new THREE.LineDashedMaterial({
          color: active ? 0xbcfa70 : 0x405d3c,
          transparent: true,
          opacity: active ? 0.8 : 0.18,
          dashSize: 0.15,
          gapSize: 0.12,
        }),
      );
      line.computeLineDistances();
      this.rayGroup.add(line);
      if (active && progress !== null) {
        const k = (((progress * echoes.length - i) % 1) + 1) % 1,
          p = new THREE.Mesh(
            new THREE.SphereGeometry(0.065, 8, 8),
            new THREE.MeshBasicMaterial({ color: 0xbcfa70 }),
          );
        p.position.lerpVectors(start, end, k);
        this.rayGroup.add(p);
      }
    });
  }
  render(t, mode, clock) {
    this.t = t;
    const changed = mode !== this.mode;
    this.mode = mode;
    this.controls.enabled = mode !== "welcome";
    if (changed && mode === "explore") this.setPreset("front");
    this.controls.autoRotate = this.orbit && this.motion;
    this.nodes.visible = mode !== "explore" || this.nodesEnabled;
    this.grid.visible = mode !== "explore" || this.blend < 0.98;
    this.rings.forEach((ring, i) => {
      let k = (clock / (mode === "explore" ? 3.5 : 2.6) + i / 5) % 1;
      const emitting = t >= 7.5 && t < 12;
      ring.visible = mode === "connect" || emitting;
      ring.scale.setScalar(0.3 + k * 12);
      ring.material.opacity = (1 - k) * (emitting ? 0.5 : 0.16);
    });
    this.nodeObjects.forEach((n, i) => {
      n.scale.setScalar(
        mode === "connect"
          ? 0.85 + smooth((t - (i * 0.8 + 0.5)) / 1.3) * 0.15
          : 1,
      );
    });
    if (this.ready) {
      const exploring = mode === "explore",
        wallProgress = exploring ? 1 : clamp((t - 12) / 3.4),
        objectProgress = exploring ? 1 : clamp((t - 16) / 4.2),
        materialProgress = exploring ? 1 : smooth((t - 20.5) / 2),
        colorProgress = exploring ? 1 : smooth((t - 22.5) / 2),
        solidWall = exploring ? this.blend : smooth((t - 14.3) / 1.7);
      this.model.visible = exploring ? this.blend > 0 : t >= 14.3;
      this.points.visible = exploring ? this.blend < 1 : t >= 12 && t < 24.5;
      this.edges.visible = exploring ? this.blend < 1 : t >= 12 && t < 24.5;
      const u = this.pointMat.uniforms;
      u.uWall.value = wallProgress;
      u.uObject.value = objectProgress;
      u.uTime.value = this.motion ? clock : 0;
      u.uOpacity.value = exploring ? 1 - this.blend : 0.65;
      u.uWallFade.value = exploring ? 1 : 1 - solidWall * 0.88;
      u.uObjectFade.value = exploring ? 1 : 1 - smooth((t - 19.5) / 3);
      this.edgeParts[0].material.opacity = exploring
        ? (1 - this.blend) * 0.5
        : smooth((t - 12) / 1.2) * 0.36 * (1 - smooth((t - 21) / 3.5));
      this.edgeParts[1].material.opacity = exploring
        ? (1 - this.blend) * 0.5
        : smooth((t - 16) / 3) * 0.4 * (1 - smooth((t - 21) / 3.5));
      if (
        this.lastTime !== t ||
        this.lastBlend !== this.blend ||
        this.lastMode !== mode
      ) {
        this.meshes.forEach((m) => {
          const original = m.userData.originalMaterial,
            structure = m.userData.isStructure;
          let amount = exploring
            ? this.blend
            : structure
              ? solidWall
              : smooth((objectProgress - m.userData.buildOrder) / 0.24);
          const restored = exploring ? this.blend === 1 : t >= 24.5;
          m.visible =
            amount > 0 &&
            !this.hidden.has(m.userData.object_id || m.name) &&
            (!this.isolated || m.userData.object_id === this.isolated);
          if (restored) m.material = original;
          else {
            m.material = m.userData.fadeMaterial;
            const mats = Array.isArray(m.material) ? m.material : [m.material];
            mats.forEach((mat) => {
              mat.opacity = mat.userData.originalOpacity * amount;
              if (exploring) mat.color.copy(mat.userData.originalColor);
              else {
                const c = mat.userData.originalColor,
                  luma = c.r * 0.2126 + c.g * 0.7152 + c.b * 0.0722;
                mat.color
                  .setRGB(0.4, 0.45, 0.42)
                  .lerp(new THREE.Color(luma, luma, luma), materialProgress)
                  .lerp(c, colorProgress);
                mat.roughness = THREE.MathUtils.lerp(
                  0.98,
                  mat.userData.originalRoughness,
                  materialProgress,
                );
                mat.metalness =
                  mat.userData.originalMetalness * materialProgress;
              }
            });
          }
        });
        this.lastTime = t;
        this.lastBlend = this.blend;
        this.lastMode = mode;
      }
    }
    this.updateLasers(t, clock, mode);
    if (
      mode !== "explore" &&
      !this.cameraMove &&
      !this.userCamera &&
      !this.orbit
    ) {
      const progress = smooth((t - 15) / 12);
      this.camera.position.copy(OVERVIEW);
      if (this.motion) {
        this.camera.position.x += Math.sin(progress * Math.PI) * 3;
        this.camera.position.z -= progress * 3;
      }
      this.controls.target.copy(CENTER);
      this.camera.fov = 44;
      this.camera.updateProjectionMatrix();
    }
    if (this.cameraMove) {
      const m = this.cameraMove,
        p = smooth((performance.now() - m.at) / (m.duration || 1));
      this.camera.position.lerpVectors(m.from, m.to, p);
      this.controls.target.lerpVectors(m.targetFrom, m.targetTo, p);
      this.camera.fov = THREE.MathUtils.lerp(m.fovFrom, m.fovTo, p);
      this.camera.updateProjectionMatrix();
      if (p >= 1) this.cameraMove = null;
    }
    this.controls.update();
    this.renderer.render(this.scene, this.camera);
  }
}
