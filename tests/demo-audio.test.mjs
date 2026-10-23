// Execute the app's actual audio/loading paths with controlled browser services.
// These checks cover loading races, not browser autoplay policy or real speakers.
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import vm from 'node:vm';
import test from 'node:test';

const app = await readFile(fileURLToPath(new URL('../demo/app.js', import.meta.url)), 'utf8');
function section(start, end) {
  const from = app.indexOf(start), to = app.indexOf(end, from);
  assert.ok(from >= 0 && to > from, `App source section missing: ${start}`);
  return app.slice(from, to);
}
const audio = section('const audioReady =', 'function toast(');
const playback = section('function stopAudio(', 'for (const [sel, icon]');
const loading = section('$("#start-scan").disabled = true;', 'if (!state.motion)');
const flush = () => new Promise(resolve => setImmediate(resolve));

function harness() {
  let resolveSound, rejectSound, resolveScene;
  const starts = [], warnings = [], elements = new Map();
  const state = { playing: false, replayAt: null, muted: false, motion: true, ready: false };
  const $ = selector => {
    if (!elements.has(selector)) elements.set(selector, {
      attributes: {}, disabled: false, setAttribute(key, value) { this.attributes[key] = value; },
    });
    return elements.get(selector);
  };
  const gainNode = () => ({
    gain: { value: 0, setValueAtTime() {}, linearRampToValueAtTime() {}, cancelAndHoldAtTime() {} },
    connect() {}, disconnect() {},
  });
  const sandbox = {
    state, $, AbortSignal, performance: { now: () => 2000 }, svg: name => name, toast() {},
    console: { warn: error => warnings.push(error), error: error => warnings.push(error) },
    fetch: () => new Promise((resolve, reject) => { resolveSound = resolve; rejectSound = reject; }),
    view: { load: () => new Promise(resolve => { resolveScene = resolve; }) },
    window: { AudioContext: class {
      currentTime = 0;
      destination = {};
      createGain() { return gainNode(); }
      decodeAudioData() { return Promise.resolve({ duration: 4.5 }); }
      resume() { return Promise.resolve(); }
      createBufferSource() {
        return { connect() {}, disconnect() {}, stop() {}, start: (when, offset) => starts.push(offset) };
      }
    } },
  };
  vm.createContext(sandbox);
  vm.runInContext(`let context, buffer, audioSource, audioGain, gain, lastSound = false;
${audio}
${playback}
${loading}
globalThis.soundComplete = audioReady;`, sandbox);
  return {
    state, $, starts, warnings,
    replay() { state.replayAt = 1000; vm.runInContext('playAudio()', sandbox); },
    async sound() {
      resolveSound({ ok: true, arrayBuffer: async () => new ArrayBuffer(0) });
      await sandbox.soundComplete;
    },
    async soundFailure() { rejectSound(new Error('Sound unavailable')); await sandbox.soundComplete; },
    async scene() { resolveScene(); await flush(); },
  };
}

test('late sound joins an active replay at its elapsed offset', async () => {
  const app = harness();
  app.replay();
  assert.deepEqual(app.starts, []);
  await app.sound();
  assert.deepEqual(app.starts, [1]);
});

for (const variant of ['stopped', 'expired', 'muted']) {
  test(`late sound does not start a ${variant} replay`, async () => {
    const app = harness();
    app.replay();
    if (variant === 'stopped') app.state.replayAt = null;
    if (variant === 'expired') app.state.replayAt = -3000;
    if (variant === 'muted') app.state.muted = true;
    await app.sound();
    assert.deepEqual(app.starts, []);
  });
}

test('scene readiness enables visual controls while sound is pending', async () => {
  const app = harness();
  assert.equal(app.$('#start-scan').disabled, true);
  await app.scene();
  assert.equal(app.state.ready, true);
  assert.equal(app.$('#start-scan').disabled, false);
  assert.equal(app.$('#explore-demo').disabled, false);
  await app.sound();
});

test('sound failure preserves a ready visual demo and disables unavailable sound', async () => {
  const app = harness();
  await app.scene();
  await app.soundFailure();
  assert.equal(app.state.ready, true);
  assert.equal(app.$('#start-scan').disabled, false);
  assert.equal(app.$('#explore-demo').disabled, false);
  assert.equal(app.state.muted, true);
  assert.equal(app.$('#sound-toggle').disabled, true);
  assert.equal(app.$('#sound-toggle').attributes['aria-label'], 'Sound unavailable');
  assert.equal(app.warnings.length, 1);
});
