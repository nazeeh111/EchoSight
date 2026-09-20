import { initEchoBot } from "./echo-bot.js";
import { RoomView } from "./scene.js";
import {
  DURATION,
  STAGES,
  stageAt,
  clamp,
  makeEchoes,
  confidenceFor,
} from "./data.js";
const $ = (s) => document.querySelector(s),
  $$ = (s) => [...document.querySelectorAll(s)];
const icons = {
  sound:
    '<path d="M11 5 6 9H3v6h3l5 4V5Z"/><path d="M15 8a6 6 0 0 1 0 8M18 5a10 10 0 0 1 0 14"/>',
  mute: '<path d="M11 5 6 9H3v6h3l5 4V5Z"/><path d="m16 9 5 6m0-6-5 6"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5"/>',
  keyboard:
    '<rect x="2" y="5" width="20" height="14" rx="2"/><path d="M6 9h.1M10 9h.1M14 9h.1M18 9h.1M6 12h.1M10 12h.1M14 12h.1M18 12h.1M7 15h10"/>',
  expand: '<path d="M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5"/>',
  fit: '<path d="M9 4H4v5m11-5h5v5M4 15v5h5m11-5v5h-5M9 9h6v6H9z"/>',
  orbit:
    '<ellipse cx="12" cy="12" rx="10" ry="5" transform="rotate(-28 12 12)"/><circle cx="12" cy="12" r="2"/>',
  play: '<path d="m8 5 11 7-11 7V5Z"/>',
  pause: '<path d="M8 5v14M16 5v14"/>',
  restart: '<path d="M4 10a8 8 0 1 1 1 7M4 4v6h6"/>',
  phone:
    '<rect x="6" y="2" width="12" height="20" rx="2"/><path d="M10 19h4"/>',
};
const svg = (name) =>
  `<svg viewBox="0 0 24 24" aria-hidden="true">${icons[name] || ""}</svg>`;
const escape = (s) =>
  String(s ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
let state = {
  page: "welcome",
  t: 0,
  playing: false,
  ready: false,
  muted: false,
  motion: !matchMedia("(prefers-reduced-motion: reduce)").matches,
  count: 3,
  seed: crypto.getRandomValues(new Uint32Array(1))[0],
  echoes: [],
  phone: 0,
  selected: null,
  connected: [true, true, true],
  replayAt: null,
  light: false,
};
state.echoes = makeEchoes(state.seed, state.count);
let view;
try {
  view = new RoomView($("#room-canvas"), selectObject);
} catch (error) {
  $("#load-status").textContent =
    "3D rendering is unavailable. Open this demo in a browser with WebGL enabled.";
  console.error(error);
}
let context,
  buffer,
  audioSource,
  audioGain,
  gain,
  lastSound = false,
  previousStage = -99,
  lastFrame = performance.now(),
  toastTimer,
  heroPulse = 0;
const audioReady = fetch("./assets/scan-sweep.wav")
  .then((r) => {
    if (!r.ok) throw Error("Sound file unavailable");
    return r.arrayBuffer();
  })
  .then((b) => {
    context = new (window.AudioContext || window.webkitAudioContext)();
    gain = context.createGain();
    gain.gain.value = 1;
    gain.connect(context.destination);
    return context.decodeAudioData(b);
  })
  .then((b) => (buffer = b))
  .catch((e) => {
    state.muted = true;
    $("#sound-toggle").title = "Sound unavailable";
    console.warn(e);
  });
function toast(message) {
  $("#toast").textContent = message;
  $("#toast").classList.add("visible");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => $("#toast").classList.remove("visible"), 3500);
}
function stopAudio() {
  if (audioSource) {
    const source = audioSource,
      fade = audioGain;
    audioSource = null;
    audioGain = null;
    try {
      const now = context.currentTime;
      fade.gain.cancelAndHoldAtTime(now);
      fade.gain.linearRampToValueAtTime(0, now + 0.06);
      source.stop(now + 0.07);
      source.onended = () => {
        source.disconnect();
        fade.disconnect();
      };
    } catch {
      source.disconnect();
      fade?.disconnect();
    }
  }
  lastSound = false;
}
function playAudio(offset = 0) {
  if (!context || !buffer || offset >= 4.5 || state.muted) return;
  stopAudio();
  audioSource = context.createBufferSource();
  audioSource.buffer = buffer;
  audioGain = context.createGain();
  audioGain.gain.setValueAtTime(0, context.currentTime);
  audioGain.gain.linearRampToValueAtTime(1, context.currentTime + 0.04);
  audioSource.connect(audioGain);
  audioGain.connect(gain);
  audioSource.start(0, Math.max(0, offset));
  lastSound = true;
}
function unlockAudio() {
  context
    ?.resume()
    .catch(() =>
      toast("Sound could not start. The visual demo remains available."),
    );
}
for (const [sel, icon] of [
  ["#sound-toggle", "sound"],
  ["#theme-toggle", "sun"],
  ["#help-toggle", "keyboard"],
  ["#fullscreen", "expand"],
  ["#reset-camera", "fit"],
  ["#orbit-toggle", "orbit"],
  ["#restart", "restart"],
  ["#play-pause", "pause"],
])
  $(sel).innerHTML = svg(icon);
function setPage(page) {
  state.page = page;
  document.body.dataset.page = page;
  $("#welcome").hidden = page !== "welcome";
  $("#workspace").hidden = page === "welcome";
  $$(".steps button").forEach((b, i) => {
    const step = ["welcome", "connect", "reconstruct", "explore"].indexOf(page);
    b.classList.toggle("active", i === step);
    b.classList.toggle("complete", i < step);
    b.setAttribute("aria-current", i === step ? "step" : "false");
  });
  $("#workspace-grid").classList.toggle("exploring", page === "explore");
  $("#workspace-grid").classList.toggle("connecting", page === "connect");
  $("#left-panel").hidden = page === "explore";
  $("#inspector").hidden = page !== "explore";
  $("#phone-cards").hidden = page !== "connect";
  $("#timeline-panel").hidden = page === "explore";
  $("#new-scan").hidden = page !== "explore";
  $("#cancel-scan").hidden = page === "explore";
  requestAnimationFrame(() => view?.resize());
}
function start() {
  if (!state.ready) return;
  state.startedAt = performance.now();
  state.completedAt = null;
  unlockAudio();
  stopAudio();
  state.t = 0;
  state.playing = true;
  state.replayAt = null;
  state.connected = Array(state.count).fill(false);
  state.seed = crypto.getRandomValues(new Uint32Array(1))[0];
  state.echoes = makeEchoes(state.seed, state.count);
  state.selected = null;
  view.hidden.clear();
  view.isolated = null;
  view.visibility();
  view.box.visible = false;
  view.dimensions.visible = false;
  view.setPreset("3d", true);
  view.blend = 1;
  view.setReplay(-1, [], null);
  setPage("connect");
  renderConnect();
  previousStage = -99;
  lastFrame = performance.now();
  updateJourney();
}
function renderConnect() {
  const connected = state.connected.filter(Boolean).length;
  $("#left-panel").innerHTML =
    `<div class="eyebrow">INVITE A NODE</div><h3 class="panel-heading">Pairing the array.</h3><div class="session-demo"><img src="assets/demo-qr.png" width="124" height="124" alt="Informational demo QR code"><p>Pairing is simulated.<br>No devices need to connect.</p></div><div class="session-code" id="demo-code">ECHO-${String(state.seed).slice(-4).padStart(4, "0")}</div><button class="plain-button" id="refresh-code">Refresh demo code ↻</button><div class="divider"></div><div class="eyebrow">YOUR PHONE ARRAY</div><div class="ready-summary"><strong id="ready-count">${connected}</strong><span>of ${state.count} <span id="ready-unit">linked</span></span></div><div class="pairing-track"><div class="pair-track-line"></div>${["Invitation ready", "Finding nearby phones", "Aligning the array", "Ready to reconstruct"].map((label, i) => `<div class="pair-step" data-pair-step="${i}"><span class="pair-dot">${i + 1}</span><span>${label}</span><i></i></div>`).join("")}</div><div class="pair-progress"><i id="pair-progress-fill"></i></div><button class="plain-button lime" id="add-phone" ${state.count >= 5 ? "disabled" : ""}>+ Add phone</button><button class="plain-button" id="manual-toggle">${state.playing ? "Pause for manual pairing" : "Resume guided scan"} ${state.playing ? "Ⅱ" : "→"}</button><button class="plain-button lime" id="begin-reconstruction">Begin reconstruction →</button><p class="estimate-note">Guided pairing continues automatically. No data leaves this device.</p>`;
  $("#phone-cards").style.setProperty("--phone-count", state.count);
  $("#phone-cards").innerHTML = Array.from(
    { length: state.count },
    (_, i) =>
      `<div class="device-card ${state.connected[i] ? "ready" : ""}" data-node="${i}"><span class="device-id">NODE 0${i + 1}</span>${svg("phone")}<div><h4>${i === 0 ? "Your phone" : `Phone 0${i + 1}`}</h4><div class="device-state">${state.connected[i] ? "Connected" : "Searching"}</div><div class="join-progress"><i></i></div><button class="device-action" data-join="${i}">${state.connected[i] ? "Disconnect" : "Simulate join →"}</button></div>${i > 2 ? `<button class="remove-phone" data-remove="${i}" aria-label="Remove phone ${i + 1}">×</button>` : ""}</div>`,
  ).join("");
  $("#add-phone").onclick = () => {
    if (state.count >= 5) return;
    state.count++;
    state.connected.push(false);
    state.echoes = makeEchoes(state.seed, state.count);
    view.makeNodes(state.count);
    renderConnect();
  };
  $("#refresh-code").onclick = () => {
    state.seed = crypto.getRandomValues(new Uint32Array(1))[0];
    state.echoes = makeEchoes(state.seed, state.count);
    $("#demo-code").textContent =
      `ECHO-${String(state.seed).slice(-4).padStart(4, "0")}`;
    toast("Demo invitation refreshed.");
  };
  $("#manual-toggle").onclick = () => {
    setPlaying(!state.playing);
    renderConnect();
  };
  $("#begin-reconstruction").onclick = () => {
    state.connected.fill(true);
    seek(5);
    setPlaying(true);
    unlockAudio();
  };
  $$("[data-join]").forEach(
    (b) =>
      (b.onclick = () => {
        setPlaying(false);
        const i = +b.dataset.join;
        state.connected[i] = !state.connected[i];
        renderConnect();
        toast(
          `Phone ${i + 1} ${state.connected[i] ? "joined the demo" : "disconnected"}.`,
        );
      }),
  );
  $$("[data-remove]").forEach(
    (b) =>
      (b.onclick = () => {
        state.count--;
        state.phone = Math.min(state.phone, state.count - 1);
        state.connected.splice(+b.dataset.remove, 1);
        state.echoes = makeEchoes(state.seed, state.count);
        view.makeNodes(state.count);
        renderConnect();
      }),
  );
  $("#stage-title").textContent = `Connect ${state.count} phones`;
  $("#stage-kicker").textContent = "PHONE ARRAY";
  $("#stage-description").textContent =
    "Different corners. One shared picture.";
  $("#stage-status").textContent = "Demo session";
  $("#view-label").textContent = "PHONE ARRAY";
  $("#view-subtitle").textContent = "SIMULATED PAIRING · NO LIVE CONNECTIONS";
  updateConnections();
}
function updateConnections() {
  const count = state.connected.filter(Boolean).length,
    display = $("#ready-count");
  if (display && display.textContent !== String(count)) {
    display.textContent = count;
    display.classList.remove("count-pop");
    void display.offsetWidth;
    display.classList.add("count-pop");
  }
  const joinedEnd = 0.7 + (state.count - 1) * 0.68 + 0.3,
    pairTime =
      count === state.count
        ? state.t
        : Math.min(state.t, 0.45 + ((joinedEnd - 0.45) * count) / state.count),
    p = clamp(pairTime / 5);
  $("#view-counter").textContent =
    `${count} / ${state.count} ${pairTime >= 4.15 ? "READY" : "LINKED"}`;
  const ranges = [
    [0, 0.45],
    [0.45, joinedEnd],
    [joinedEnd, 4.15],
    [4.15, 5],
  ];
  $$(".pair-step").forEach((el, i) => {
    const [a, b] = ranges[i],
      local = clamp((pairTime - a) / (b - a));
    el.classList.toggle("active", local > 0 && local < 1);
    el.classList.toggle("done", local >= 1);
    el.style.setProperty("--pair-p", local);
    el.querySelector(".pair-dot").textContent =
      local >= 1 ? "✓" : String(i + 1);
  });
  if ($("#pair-progress-fill"))
    $("#pair-progress-fill").style.transform = `scaleX(${p})`;
  if ($("#ready-unit"))
    $("#ready-unit").textContent = pairTime >= 4.15 ? "ready" : "linked";
  $$(".device-card").forEach((el, i) => {
    const connected = state.connected[i];
    el.classList.toggle("ready", connected);
    el.classList.toggle(
      "connecting",
      !connected && state.playing && state.t > i * 0.68,
    );
    el.querySelector(".device-state").textContent = connected
      ? pairTime >= 4.15
        ? "Ready"
        : "Connected"
      : "Searching";
    el.querySelector("[data-join]").textContent = connected
      ? "Disconnect"
      : "Simulate join →";
    el.querySelector(".join-progress i").style.transform =
      `scaleX(${connected ? 1 : state.playing ? clamp((state.t - i * 0.68) / 0.7) : 0})`;
  });
  const qr = $(".session-demo");
  if (qr) {
    qr.style.setProperty("--scan-progress", p);
    qr.classList.toggle("pairing", state.playing && state.t < 4.15);
    qr.classList.toggle("paired", pairTime >= 4.15);
  }
}
function renderStages() {
  const i = stageAt(state.t),
    stage = STAGES[i];
  $("#left-panel").innerHTML =
    `<div class="eyebrow">ACOUSTIC EVIDENCE</div><div class="stage-summary"><h3 class="panel-heading">${stage.heading}</h3><p class="panel-copy">${stage.text}</p></div><div class="mini-wave">${Array.from({ length: 44 }, (_, j) => `<i style="--h:${6 + Math.sin(j * 1.4) ** 2 * 22}px;--delay:${-j * 0.08}s"></i>`).join("")}</div><div class="build-order">${["Walls", "Objects", "Materials", "Color"].map((label, i) => `<div data-build-step="${i}"><span>${String(i + 1).padStart(2, "0")}</span>${label}<i></i></div>`).join("")}</div><ol class="stage-list">${STAGES.map((s, j) => `<li data-stage="${j}" class="${j === i ? "active" : j < i ? "done" : ""}"><span class="stage-index">${j < i ? "✓" : String(j + 1).padStart(2, "0")}</span><h4>${s.title}</h4><small>${j < i ? "Done" : `${s.end - s.at}s`}</small></li>`).join("")}</ol><div class="divider"></div><p class="estimate-note">Simulated reconstruction.<br>Final geometry from your room model.</p>`;
}
function updateJourney() {
  if (state.page === "welcome" || state.page === "explore") return;
  const stage = stageAt(state.t);
  if (state.t >= DURATION) {
    finish();
    return;
  }
  if (stage < 0) {
    if (state.page !== "connect") {
      setPage("connect");
      renderConnect();
    }
    if (state.playing) {
      let changed = false;
      state.connected = state.connected.map((c, i) => {
        const v = state.t >= 0.7 + i * 0.68;
        if (c !== v) changed = true;
        return v;
      });
      if (changed) updateConnections();
    }
    updateConnections();
    $("#view-message").innerHTML =
      state.t < 3.3
        ? "Finding a shared rhythm<b>Phones join one by one</b>"
        : "Array synchronized<b>A moment to settle before the first sound</b>";
    $("#transport-status").textContent = "CONNECTING YOUR PHONE ARRAY";
  } else {
    if (state.page !== "reconstruct") setPage("reconstruct");
    if (previousStage !== stage) {
      renderStages();
      $("#stage-title").textContent = STAGES[stage].title;
      $("#stage-kicker").textContent = "RECONSTRUCTION";
      $("#stage-description").textContent = STAGES[stage].heading;
      $("#stage-status").textContent = "Reconstructing";
      $("#view-label").textContent =
        `${String(stage + 1).padStart(2, "0")} / ${STAGES[stage].title.toUpperCase()}`;
      $("#view-subtitle").textContent = "SIMULATED ACOUSTIC RECONSTRUCTION";
      $("#left-panel").classList.toggle("listening", stage === 1);
      $("#transport-status").textContent = STAGES[stage].status;
    }
    $("#view-counter").textContent =
      stage < 2
        ? `${state.count} PHONES · SYNCHRONIZED`
        : `${Math.round(clamp((state.t - 12) / 12) * 32000).toLocaleString()} SURFACE SAMPLES`;
    $("#view-message").innerHTML =
      stage === 1
        ? `Emitting a gentle sweep <span class="emission-time">${Math.max(0, 12 - state.t).toFixed(1)}s</span><b>Soft volume · 420–2100 Hz</b>`
        : stage === 0
          ? "The array settles into sync<b>The first pulse is almost ready</b>"
          : stage === 8
            ? "Your room, brought to life."
            : stage === 2
              ? "Tracing the room boundaries."
              : stage === 3
                ? "Walls take shape first."
                : stage === 4
                  ? "Three views. One connected structure."
                  : stage === 5
                    ? "Placing the objects, row by row."
                    : stage === 6
                      ? "Resolving surface materials."
                      : "Bringing the room into color.";
  }
  const ranges = [
    [12, 16],
    [16, 20.5],
    [20.5, 22.5],
    [22.5, 24.5],
  ];
  $$("[data-build-step]").forEach((el, i) => {
    const p = clamp((state.t - ranges[i][0]) / (ranges[i][1] - ranges[i][0]));
    el.classList.toggle("active", p > 0 && p < 1);
    el.classList.toggle("done", p >= 1);
    el.style.setProperty("--build-p", p);
  });
  previousStage = stage;
  $("#timeline").value = state.t;
  $("#time-display").textContent =
    `${state.t.toFixed(1).padStart(4, "0")} / 27.0`;
  $("#progress-number").textContent = `${Math.round((state.t / 27) * 100)}%`;
  $("#play-pause").innerHTML = svg(state.playing ? "pause" : "play");
  $("#play-pause").setAttribute(
    "aria-label",
    state.playing ? "Pause scan" : "Resume scan",
  );
}
function finish() {
  state.completedAt = performance.now();
  state.t = 27;
  state.playing = false;
  state.replayAt = null;
  stopAudio();
  view.setReplay(-1, [], null);
  state.selected = null;
  view.box.visible = false;
  setPage("explore");
  $("#stage-kicker").textContent = "ROOM EXPLORER";
  $("#stage-title").textContent = "Room resolved";
  $("#stage-description").textContent = "Your room, brought to life.";
  $("#stage-status").textContent = "Room model";
  $("#view-label").textContent = "ROOM 01 / RESOLVED";
  $("#view-subtitle").textContent = "ROOM GEOMETRY · ORIGINAL MATERIALS";
  $("#view-counter").textContent = `${view.meshes.length} MESHES`;
  $("#view-message").innerHTML = "";
  view.blend = 1;
  view.nodesEnabled = false;
  view.setPreset("front");
  renderInspector();
}
function seek(t) {
  stopAudio();
  state.replayAt = null;
  view.setReplay(-1, [], null);
  state.t = clamp(t, 0, 27);
  state.connected = state.connected.map((_, i) => state.t >= 0.7 + i * 0.68);
  previousStage = -99;
  if (state.t >= 27) {
    finish();
    return;
  }
  setPage(state.t < 5 ? "connect" : "reconstruct");
  if (state.t < 5) renderConnect();
  updateJourney();
}
function setPlaying(value) {
  state.playing = value;
  lastFrame = performance.now();
  if (!value) stopAudio();
  updateJourney();
}
function renderInspector() {
  const categories = new Map();
  view.groups.forEach((g) => {
    const c = g.meta.category || "Room elements";
    if (!categories.has(c)) categories.set(c, []);
    categories.get(c).push(g);
  });
  $("#inspector").innerHTML =
    `<section class="inspector-section"><h3>Scene controls <button id="scene-reset" class="inspector-reset">Reset</button></h3><div class="eyebrow">RENDER MODE</div><div class="inspector-label"><span>Scan</span><span id="blend-value">100% model</span></div><input type="range" id="blend" min="0" max="100" value="100" aria-label="Scan to model blend"><button class="plain-button" id="raw-scan">Hold for raw scan</button><div class="segmented" aria-label="Camera presets"><button data-view="3d">3D</button><button data-view="top">Top</button><button data-view="front" class="active">Inside</button><button data-view="source">Source</button></div><button class="toggle-row" id="nodes-toggle" aria-pressed="false"><span>Phone nodes</span><span class="switch"></span></button><button class="toggle-row" id="dimensions-toggle" aria-pressed="false"><span>Dimensions (model)</span><span class="switch"></span></button><p class="estimate-note">Original ceiling transparency retained.</p></section><section class="inspector-section"><h3>Scene objects <span class="muted-count">${view.groups.length}</span></h3><label class="sr-only" for="object-select">Inspect a room object</label><select class="object-select" id="object-select"><option value="">Select an object to inspect</option>${[...categories].map(([cat, groups]) => `<optgroup label="${escape(cat)}">${groups.map((g) => `<option value="${escape(g.id)}">${escape(g.name)}</option>`).join("")}</optgroup>`).join("")}</select><div id="selected-object"><p class="echo-note">Click an object in the room, or choose one above.</p></div><button class="plain-button" id="show-all-objects">Show all objects</button></section><section class="inspector-section"><h3>Signal sources</h3><div class="echo-phone-tabs"><button data-phone="-1">HUB</button>${Array.from({ length: state.count }, (_, i) => `<button data-phone="${i}" class="${i === state.phone ? "active" : ""}">0${i + 1}</button>`).join("")}</div><div id="echo-details"></div></section><section class="inspector-section"><a class="download-link" href="assets/room-corrected.glb" download>Download room model <span>↓</span></a></section>`;
  $("#blend").oninput = (e) => {
    view.blend = +e.target.value / 100;
    $("#blend-value").textContent = `${e.target.value}% model`;
  };
  let heldBlend = 1,
    holding = false;
  const raw = $("#raw-scan");
  function release() {
    if (!holding) return;
    holding = false;
    view.blend = heldBlend;
    raw.classList.remove("active");
  }
  raw.onpointerdown = (e) => {
    e.preventDefault();
    heldBlend = view.blend;
    holding = true;
    view.blend = 0;
    raw.classList.add("active");
    raw.setPointerCapture(e.pointerId);
  };
  raw.onpointerup = release;
  raw.onpointercancel = release;
  raw.onlostpointercapture = release;
  raw.onkeydown = (e) => {
    if ((e.key === " " || e.key === "Enter") && !e.repeat) {
      e.preventDefault();
      heldBlend = view.blend;
      holding = true;
      view.blend = 0;
    }
  };
  raw.onkeyup = release;
  raw.onblur = release;
  $$("[data-view]").forEach(
    (b) =>
      (b.onclick = () => {
        $$("[data-view]").forEach((x) => x.classList.toggle("active", x === b));
        view.setPreset(b.dataset.view);
      }),
  );
  $("#nodes-toggle").onclick = (e) => {
    view.nodesEnabled = !view.nodesEnabled;
    e.currentTarget.setAttribute("aria-pressed", view.nodesEnabled);
  };
  $("#dimensions-toggle").onclick = (e) => {
    view.dimensions.visible = !view.dimensions.visible;
    e.currentTarget.setAttribute("aria-pressed", view.dimensions.visible);
  };
  $("#scene-reset").onclick = () => {
    view.hidden.clear();
    view.isolated = null;
    view.visibility();
    view.blend = 1;
    view.nodesEnabled = false;
    view.dimensions.visible = false;
    view.box.visible = false;
    state.selected = null;
    view.setPreset("front");
    renderInspector();
  };
  $("#object-select").onchange = (e) => selectObject(e.target.value);
  $("#show-all-objects").onclick = () => {
    view.hidden.clear();
    view.isolated = null;
    view.visibility();
    if (state.selected) selectObject(state.selected);
    toast("All room objects are visible.");
  };
  $$("[data-phone]").forEach(
    (b) =>
      (b.onclick = () => {
        state.phone = +b.dataset.phone;
        state.replayAt = null;
        stopAudio();
        renderEchoes();
        $$("[data-phone]").forEach((x) =>
          x.classList.toggle("active", x === b),
        );
        view.nodesEnabled = true;
        $("#nodes-toggle").setAttribute("aria-pressed", "true");
        view.setReplay(state.phone, state.echoes[state.phone] || [], null);
      }),
  );
  renderEchoes();
}
function selectObject(id) {
  state.selected = id;
  const g = view.groupMap.get(id);
  view.select(id);
  if (!g) {
    $("#selected-object").innerHTML =
      '<p class="echo-note">Choose an object to see its estimates.</p>';
    return;
  }
  $("#object-select").value = id;
  const m = g.meta,
    c = confidenceFor(id + state.seed),
    size = g.bounds.max.clone().sub(g.bounds.min),
    ceiling = /ceiling/i.test(g.name);
  if (ceiling) {
    c.material = "MEDIUM";
    c.color = "HIGH";
    c.geometry = "HIGH";
  }
  const material = ceiling
    ? "Painted plasterboard or ceiling panel; substrate unconfirmed"
    : m.material_estimate ||
      "Painted or composite surface; substrate unconfirmed";
  $("#selected-object").innerHTML =
    `<div class="object-info"><h4>${escape(g.name)}</h4><dl><dt>Component</dt><dd>${escape(m.component || "Surface")}</dd><dt>Material · estimate</dt><dd>${escape(material)}</dd><dt>Color · estimate</dt><dd>${escape(ceiling ? "White" : m.color_estimate || "Neutral")}</dd><dt>Model dimensions</dt><dd>${size.x.toFixed(2)} × ${size.z.toFixed(2)} × ${size.y.toFixed(2)} m</dd><dt>Illustrative confidence</dt></dl><span class="confidence">Material · <strong>${c.material}</strong></span><span class="confidence">Color · <strong>${c.color}</strong></span><span class="confidence">Geometry · <strong>${c.geometry}</strong></span><p class="estimate-note">Rough visual estimates. Confidence badges are simulated, not measured probabilities.</p></div><div class="control-row"><button class="plain-button" id="isolate-object">${view.isolated === id ? "Show full room" : "Isolate object"}</button><button class="plain-button" id="hide-object">${view.hidden.has(id) ? "Show object" : "Hide object"}</button></div>`;
  $("#isolate-object").onclick = () => {
    view.isolate(id);
    selectObject(id);
  };
  $("#hide-object").onclick = () => {
    if (view.hidden.has(id)) view.hidden.delete(id);
    else view.hidden.add(id);
    view.visibility();
    selectObject(id);
  };
  $("#object-hint").hidden = false;
  $("#object-hint").textContent = g.name;
  setTimeout(() => ($("#object-hint").hidden = true), 2400);
}
function renderEchoes() {
  const echoes = state.echoes[state.phone] || [],
    hub = state.phone < 0;
  $("#echo-details").innerHTML =
    `<div class="echo-summary"><span>${hub ? "Computer · sound source" : `Phone 0${state.phone + 1} · received echoes`}</span><strong>${hub ? "4.5 s" : `${echoes.length} paths`}</strong></div><canvas class="wave-canvas" id="wave-canvas" aria-label="${hub ? "Emitted sound waveform" : "Simulated incoming echo waveform"}"></canvas><button class="echo-replay" id="echo-replay">${hub ? "Replay soft sweep ▷" : "Replay arrivals ▷"}</button>${hub ? '<p class="echo-note">A soft 420–2100 Hz sweep. Smooth onset and release, at a restrained level.</p>' : `<p class="echo-note">Arrival direction: 0° = top of the floor plan, clockwise.<br>Every angle has the same uncertainty: ±10°.</p><ol class="echo-list">${echoes.map((e, i) => `<li data-echo="${i}"><span class="echo-icon" style="transform:rotate(${e.angle}deg)">↑</span><span>${e.direction}<small class="echo-delay">${e.delay.toFixed(1)} ms</small></span><span class="echo-angle">${e.angle}° ±10°</span></li>`).join("")}</ol><p class="estimate-note">${echoes.length} illustrative arrivals. Replayed slowly for clarity.</p>`}`;
  $("#echo-replay").onclick = () => {
    unlockAudio();
    if (state.replayAt !== null) {
      state.replayAt = null;
      stopAudio();
      view.setReplay(state.phone, echoes, null);
    } else {
      state.replayAt = performance.now();
      playAudio();
      view.nodesEnabled = true;
      $("#nodes-toggle").setAttribute("aria-pressed", "true");
    }
    $("#echo-replay").textContent =
      state.replayAt !== null
        ? "Stop replay ■"
        : hub
          ? "Replay soft sweep ▷"
          : "Replay arrivals ▷";
  };
  drawWave(0);
}
function drawWave(progress) {
  const canvas = $("#wave-canvas");
  if (!canvas) return;
  const w = canvas.clientWidth || 230,
    h = 50,
    d = Math.min(devicePixelRatio, 2);
  if (canvas.width !== w * d) {
    canvas.width = w * d;
    canvas.height = h * d;
  }
  const ctx = canvas.getContext("2d");
  ctx.setTransform(d, 0, 0, d, 0, 0);
  ctx.clearRect(0, 0, w, h);
  ctx.strokeStyle = state.light ? "#547d22" : "#90c45b";
  ctx.lineWidth = 1;
  const es = state.echoes[state.phone] || [];
  ctx.beginPath();
  for (let x = 0; x < w; x++) {
    const p = x / w,
      envelope =
        state.phone < 0
          ? Math.sin(Math.PI * p) * 0.7
          : es.reduce(
              (s, e, i) =>
                s +
                Math.exp(
                  -Math.pow((p - (i + 0.5) / es.length) * es.length * 5, 2),
                ) *
                  e.amplitude,
              0,
            ),
      y = h / 2 + Math.sin(x * 1.7) * envelope * 18;
    if (x === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  }
  ctx.stroke();
  if (state.replayAt !== null) {
    ctx.strokeStyle = "#c3ff7a";
    ctx.beginPath();
    ctx.moveTo(progress * w, 4);
    ctx.lineTo(progress * w, h - 4);
    ctx.stroke();
  }
}
function toggleMute() {
  state.muted = !state.muted;
  $("#sound-toggle").innerHTML = svg(state.muted ? "mute" : "sound");
  $("#sound-toggle").setAttribute(
    "aria-label",
    state.muted ? "Unmute sound" : "Mute sound",
  );
  $("#sound-toggle").title = state.muted ? "Sound off" : "Sound on";
  if (state.muted) stopAudio();
  else unlockAudio();
  toast(state.muted ? "Sound muted." : "Sound on. The sweep plays softly.");
}
function home() {
  state.playing = false;
  state.replayAt = null;
  stopAudio();
  setPage("welcome");
}
$("#start-scan").onclick = start;
$("#new-scan").onclick = start;
$("#explore-demo").onclick = () => {
  if (state.ready) {
    unlockAudio();
    finish();
  }
};
$("#home").onclick = home;
$("#cancel-scan").onclick = home;
$("#play-pause").onclick = () => {
  unlockAudio();
  setPlaying(!state.playing);
};
$("#restart").onclick = start;
$("#timeline").oninput = (e) => seek(+e.target.value);
$("#sound-toggle").onclick = toggleMute;
$("#theme-toggle").onclick = () => {
  state.light = !state.light;
  document.body.classList.toggle("light", state.light);
  $("#theme-toggle").setAttribute(
    "aria-label",
    `Switch to ${state.light ? "dark" : "light"} theme`,
  );
  drawWave(0);
};
$("#help-toggle").onclick = () => $("#help-dialog").showModal();
$("#close-help").onclick = () => $("#help-dialog").close();
$("#fullscreen").onclick = () => {
  if (document.fullscreenElement) document.exitFullscreen();
  else
    document.documentElement
      .requestFullscreen?.()
      .catch(() => toast("Fullscreen is unavailable in this browser."));
};
$("#reset-camera").onclick = () =>
  view.setPreset(state.page === "explore" ? "front" : "3d");
$("#orbit-toggle").onclick = (e) => {
  view.orbit = !view.orbit;
  view.userCamera = true;
  e.currentTarget.classList.toggle("active", view.orbit);
  e.currentTarget.setAttribute(
    "aria-label",
    view.orbit ? "Stop auto orbit" : "Start auto orbit",
  );
};
$("#zoom-in").onclick = () => {
  view.userCamera = true;
  view.camera.position
    .sub(view.controls.target)
    .multiplyScalar(0.84)
    .add(view.controls.target);
};
$("#zoom-out").onclick = () => {
  view.userCamera = true;
  view.camera.position
    .sub(view.controls.target)
    .multiplyScalar(1.18)
    .add(view.controls.target);
};
$("#motion-toggle").onclick = () => {
  state.motion = !state.motion;
  view.motion = state.motion;
  document.body.classList.toggle("reduced-motion", !state.motion);
  $("#motion-toggle").innerHTML =
    `Motion ${state.motion ? "on" : "reduced"} <span>∿</span>`;
};
$$(".steps button").forEach(
  (b) =>
    (b.onclick = () => {
      if (b.dataset.page === state.page) return;
      if (b.dataset.page === "welcome") home();
      else if (state.ready) {
        unlockAudio();
        if (b.dataset.page === "explore") finish();
        else {
          state.playing = false;
          seek(b.dataset.page === "connect" ? 0 : 5);
        }
      }
    }),
);
$("#send-pulse").onclick = () => {
  heroPulse = performance.now();
  toast("One pulse. Many paths. Every echo describes a surface.");
};
document.addEventListener("keydown", (e) => {
  if (
    document.activeElement?.closest("#echo-bot") ||
    /INPUT|SELECT|TEXTAREA|BUTTON/.test(document.activeElement?.tagName) ||
    $("#help-dialog").open
  )
    return;
  if (e.code === "Space" && ["connect", "reconstruct"].includes(state.page)) {
    e.preventDefault();
    setPlaying(!state.playing);
  }
  if (e.key.toLowerCase() === "m") toggleMute();
  if (e.key.toLowerCase() === "r" && state.page !== "welcome")
    view.setPreset(state.page === "explore" ? "front" : "3d");
});
document.addEventListener("visibilitychange", () => {
  if (document.hidden) {
    if (state.playing) setPlaying(false);
    state.replayAt = null;
    stopAudio();
  }
});
$("#start-scan").disabled = true;
$("#explore-demo").disabled = true;
if (view) {
  view.motion = state.motion;
  view
    .load()
    .then(async () => {
      await audioReady;
      state.ready = true;
      $("#start-scan").disabled = false;
      $("#explore-demo").disabled = false;
      $("#load-status").textContent = "";
    })
    .catch((error) => {
      $("#load-status").textContent =
        "The room could not load. Refresh to retry.";
      console.error(error);
    });
}
if (!state.motion) {
  document.body.classList.add("reduced-motion");
  $("#motion-toggle").innerHTML = "Motion reduced <span>∿</span>";
}
const canvas = $("#network-canvas"),
  ctx = canvas.getContext("2d");
function drawHero(t) {
  const w = canvas.clientWidth,
    h = canvas.clientHeight,
    d = Math.min(devicePixelRatio, 2);
  if (!w || !h) return;
  if (canvas.width !== w * d || canvas.height !== h * d) {
    canvas.width = w * d;
    canvas.height = h * d;
  }
  ctx.setTransform(d, 0, 0, d, 0, 0);
  ctx.clearRect(0, 0, w, h);
  const p = (x, y) => [w * x, h * y],
    nodes = [p(0.2, 0.67), p(0.84, 0.61), p(0.69, 0.24)],
    hub = p(0.53, 0.49);
  ctx.lineWidth = 1;
  ctx.strokeStyle = state.light ? "#8caa78" : "#405444";
  const v = [
    [0.22, 0.35],
    [0.6, 0.1],
    [0.86, 0.32],
    [0.48, 0.57],
    [0.22, 0.68],
    [0.6, 0.43],
    [0.86, 0.65],
    [0.48, 0.9],
  ].map((q) => p(...q));
  [
    [0, 1],
    [1, 2],
    [2, 3],
    [3, 0],
    [0, 4],
    [1, 5],
    [2, 6],
    [3, 7],
    [4, 5],
    [5, 6],
    [6, 7],
    [7, 4],
  ].forEach(([a, b]) => {
    ctx.beginPath();
    ctx.moveTo(...v[a]);
    ctx.lineTo(...v[b]);
    ctx.stroke();
  });
  for (let i = 0; i < 4; i++) {
    const k = (t / 5500 + i / 4) % 1;
    ctx.beginPath();
    ctx.ellipse(...hub, w * 0.62 * k, h * 0.3 * k, -0.25, 0, Math.PI * 2);
    ctx.strokeStyle = state.light
      ? `rgba(77,122,30,${(1 - k) * 0.5})`
      : `rgba(188,250,112,${(1 - k) * 0.33})`;
    ctx.stroke();
  }
  if (heroPulse && performance.now() - heroPulse < 2200) {
    const k = (performance.now() - heroPulse) / 2200;
    ctx.beginPath();
    ctx.ellipse(...hub, w * 0.62 * k, h * 0.3 * k, -0.25, 0, Math.PI * 2);
    ctx.strokeStyle = `rgba(188,250,112,${1 - k})`;
    ctx.stroke();
  }
  nodes.forEach((n, i) => {
    ctx.beginPath();
    ctx.moveTo(...hub);
    ctx.lineTo(...n);
    ctx.strokeStyle = "#526d35";
    ctx.stroke();
    ctx.strokeStyle = "#a9c494";
    ctx.strokeRect(n[0] - 5, n[1] - 12, 10, 23);
    ctx.fillStyle = state.light ? "#4c6d3d" : "#7a9181";
    ctx.font = "10px monospace";
    ctx.fillText("N0" + (i + 1), n[0] + 14, n[1] + 4);
    ctx.beginPath();
    ctx.ellipse(...n, 25, 12, 0, 0, Math.PI * 2);
    ctx.strokeStyle = "#699b3a";
    ctx.stroke();
  });
  ctx.fillStyle = state.light ? "#a6c685" : "#1c3420";
  ctx.strokeStyle = "#a5c98d";
  ctx.fillRect(hub[0] - 25, hub[1] - 24, 50, 32);
  ctx.strokeRect(hub[0] - 25, hub[1] - 24, 50, 32);
  ctx.beginPath();
  ctx.moveTo(hub[0] - 30, hub[1] + 12);
  ctx.lineTo(hub[0] + 30, hub[1] + 12);
  ctx.moveTo(hub[0], hub[1] + 13);
  ctx.lineTo(hub[0], hub[1] + 25);
  ctx.moveTo(hub[0] - 17, hub[1] + 25);
  ctx.lineTo(hub[0] + 17, hub[1] + 25);
  ctx.stroke();
  ctx.fillStyle = state.light ? "#4c6d3d" : "#94ac91";
  ctx.fillText("HUB", hub[0] + 40, hub[1]);
}
function frame(now) {
  const dt = (now - lastFrame) / 1000;
  lastFrame = now;
  if (state.playing) {
    state.t = Math.min(27, state.t + dt);
    updateJourney();
  }
  const scanSound =
    state.playing &&
    state.t >= 7.5 &&
    state.t < 12 &&
    state.page === "reconstruct";
  if (scanSound && !lastSound) playAudio(state.t - 7.5);
  if (!scanSound && lastSound && state.replayAt === null) stopAudio();
  if (state.page === "welcome") drawHero(state.motion ? now : 3200);
  else
    view?.render(
      state.t,
      state.page === "reconstruct" ? "scan" : state.page,
      (state.motion ? now : 3000) / 1000,
    );
  if (view) {
    $("#orbit-toggle").classList.toggle("active", view.orbit);
    $("#orbit-toggle").setAttribute(
      "aria-label",
      view.orbit ? "Stop auto orbit" : "Start auto orbit",
    );
  }
  if (state.replayAt !== null) {
    const p = clamp((now - state.replayAt) / 4500);
    drawWave(p);
    $$("[data-echo]").forEach((el, i) =>
      el.classList.toggle(
        "active",
        Math.floor(p * (state.echoes[state.phone]?.length || 0)) === i,
      ),
    );
    if (view && state.phone >= 0)
      view.setReplay(state.phone, state.echoes[state.phone], p);
    if (p >= 1) {
      state.replayAt = null;
      stopAudio();
      $("#echo-replay").textContent =
        state.phone < 0 ? "Replay soft sweep ▷" : "Replay arrivals ▷";
      view.setReplay(state.phone, state.echoes[state.phone] || [], null);
    }
  }
  requestAnimationFrame(frame);
}
requestAnimationFrame(frame);
window.echoSight = {
  get state() {
    return {
      ...state,
      meshCount: view?.meshes?.length,
      groupCount: view?.groups?.length,
      allModelMaterialsRestored: view?.meshes?.every(
        (m) => m.material === m.userData.originalMaterial,
      ),
    };
  },
  seek(t) {
    state.playing = false;
    seek(t);
  },
  start,
  finish,
  view,
  renderAt(t) {
    state.playing = false;
    seek(t);
    view.cameraMove = null;
    if (t >= 27) view.setPreset("front", true);
    view.render(t, t >= 27 ? "explore" : t < 5 ? "connect" : "scan", t);
    drawHero(t * 1000);
  },
  ready: () => state.ready,
};

// Echo Bot suggests navigation. Only an explicit user click can move the app.
window.addEventListener("echobot:navigate", (event) => {
  const action = event.detail?.action;
  if (action === "welcome") {
    home();
    return;
  }
  if (!state.ready) {
    toast("The room is still loading. Try again in a moment.");
    return;
  }
  if (action === "start_scan") {
    start();
    return;
  }
  if (action === "connect" || action === "reconstruct") {
    state.playing = false;
    seek(action === "connect" ? 0 : 5);
    return;
  }
  if (action === "explore") {
    finish();
    return;
  }
  if (action === "replay_echoes") {
    if (state.page !== "explore") finish();
    $("#echo-details")?.scrollIntoView({
      behavior: state.motion ? "smooth" : "auto",
      block: "nearest",
    });
    if (state.replayAt === null) $("#echo-replay")?.click();
  }
});
initEchoBot();
