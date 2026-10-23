import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import vm from 'node:vm';
import { webcrypto } from 'node:crypto';
import test from 'node:test';
const sources = Object.fromEntries(await Promise.all(['workspace', 'workspace-data', 'result-data', 'comparison'].map(async n => [n, await readFile(new URL(`../demo/${n}.js`, import.meta.url), 'utf8')])));
const config = { enabled: true, token: 'a'.repeat(43), limits: { recording_bytes: 64*1024*1024, archive_bytes: 256*1024*1024, json_bytes: 1024*1024 } };
const reply = (value, status = 200) => ({ ok: status < 400, status, json: async () => structuredClone(value), text: async () => JSON.stringify(value) });
const settle = async () => { for (let i = 0; i < 10; i++) await new Promise(resolve => setImmediate(resolve)); };
class Element {
  value = ''; textContent = ''; files = []; listeners = {}; hidden = false; disabled = false;
  addEventListener(type, fn) { this.listeners[type] = fn; }
  async fire(type) { return this.listeners[type]?.({ target: this }); }
}
async function fixture(handler = () => { throw new Error('Unexpected request'); }, hash = '') {
  const nodes = new Map(), calls = [], opened = [], revisions = []; let display = 0;
  const document = { querySelector(selector) { if (!nodes.has(selector)) nodes.set(selector, new Element()); return nodes.get(selector); } };
  const location = { pathname: '/ui/results.html', hash };
  const history = { replaceState(_state, _title, value) { location.hash = value.slice(value.indexOf('#')); } };
  const fetcher = async (path, opts = {}) => { calls.push({ path, opts }); return path === '/ui/config' ? reply(config) : handler(path, opts); };
  const context = vm.createContext({ TextEncoder, AbortSignal, AbortController, DOMException, URLSearchParams, crypto: webcrypto, setTimeout, clearTimeout });
  const data = new vm.SourceTextModule(sources['workspace-data'], { context });
  const resultData = new vm.SourceTextModule(sources['result-data'], { context });
  const results = new vm.SyntheticModule(['getDisplayVersion', 'openBackendResult', 'markSessionRevision', 'getBackendResult', 'subscribeBackendResult'], function () {
    this.setExport('getDisplayVersion', () => display);
    this.setExport('getBackendResult', () => undefined); this.setExport('subscribeBackendResult', () => {});
    this.setExport('openBackendResult', (value, name) => { opened.push({ value, name }); display++; });
    this.setExport('markSessionRevision', value => revisions.push(value));
  }, { context });
  const comparison = new vm.SourceTextModule(sources.comparison, { context });
  const page = new vm.SourceTextModule(sources.workspace, { context });
  await page.link(name => ({ './workspace-data.js': data, './results.js': results, './result-data.js': resultData, './comparison.js': comparison })[name]);
  await page.evaluate();
  const app = await page.namespace.initWorkspace(document, location, history, fetcher);
  return { app, helpers: data.namespace, calls, opened, revisions, location, get: name => document.querySelector(`#workspace-${name}`), manualImport: () => display++ };
}
const session = (revision = 0, captures = []) => ({ session_id: 'session1', revision, captures });
const capture = (id, name) => ({ capture_id: id, recording_path: name, provenance: 'simulated', receiver_position_m: [1, 2, 3] });
const file = (name, content = 'wav') => ({ name, size: Buffer.byteLength(content), arrayBuffer: async () => Uint8Array.from(Buffer.from(content)).buffer });
async function resume(f, id = 'session1') { f.get('resume-id').value = id; await f.get('resume').fire('click'); }

test('upload plans require explicit provenance, unique identity, exact selected files and bounded headers', async () => {
  const f = await fixture(), h = f.helpers, p = capture('c1', 'original.wav'), wav = file('original.wav');
  assert.equal(h.planUploads([p], [wav])[0].metadata.recording_path, undefined);
  assert.throws(() => h.planUploads([{ ...p, provenance: undefined }], [wav]), /Declare provenance/);
  assert.throws(() => h.planUploads([p], [wav, file('extra.wav')]), /extra files/);
  assert.throws(() => h.planUploads([p, p], [wav]), /unique/);
  assert.throws(() => h.planUploads([{ ...p, notes: 'ü'.repeat(2000) }], [wav]), /8 KiB/);
  assert.throws(() => h.requireId(['session1']), /valid/);
  assert.throws(() => h.captureMetadata({ ...p, receiver_position_m: [NaN, 1, 2] }), /Invalid/);
  assert.equal(h.asciiJSON({ notes: '室😀' }), '{"notes":"\\u5ba4\\ud83d\\ude00"}');
});

test('client uses transient same-origin token, byte checksum, and never overwrites existing originals', async () => {
  const f = await fixture((path, opts) => reply({ capture_id: 'c1' }));
  const entry = f.helpers.planUploads([capture('c1', 'original.wav')], [file('original.wav')])[0];
  await f.app.client.upload('session1', entry);
  const { path, opts } = f.calls.at(-1);
  assert.equal(path, '/v1/sessions/session1/recordings');
  assert.equal(opts.headers['X-EchoSight-UI-Token'], config.token);
  assert.match(opts.headers['X-Recording-SHA256'], /^[a-f0-9]{64}$/);
  assert.equal(opts.credentials, 'omit'); assert.equal(opts.redirect, 'error'); assert.equal(opts.mode, 'same-origin');
  const stored = { ...entry.metadata, sha256: opts.headers['X-Recording-SHA256'] }, count = f.calls.length;
  assert.equal((await f.app.client.upload('session1', entry, stored)).skipped, true);
  await assert.rejects(f.app.client.upload('session1', entry, { ...stored, sha256: '0'.repeat(64) }), /different bytes/);
  await assert.rejects(f.app.client.upload('session1', entry, { ...stored, provenance: 'measured' }), /metadata differs/);
  await assert.rejects(f.app.client.upload('session1', { ...entry, expected: '0'.repeat(64) }), /Checksum differs/);
  assert.equal(f.calls.length, count);
});

test('partial import refreshes stored captures and retry skips identical originals', async () => {
  let captures = [], failSecond = true, posts = [];
  const f = await fixture((path, opts) => {
    if (opts.method !== 'POST') return reply(session(captures.length, captures));
    const meta = JSON.parse(opts.headers['X-Capture-Metadata']); posts.push(meta.capture_id);
    if (meta.capture_id === 'c2' && failSecond) { failSecond = false; throw new Error('Connection lost'); }
    const value = { ...meta, sha256: opts.headers['X-Recording-SHA256'] }; captures.push(value); return reply(value);
  });
  await resume(f); f.get('plan').value = JSON.stringify([capture('c1', 'one.wav'), capture('c2', 'two.wav')]);
  f.get('recordings').files = [file('one.wav'), file('two.wav', 'two')];
  await f.get('upload').fire('click');
  assert.match(f.get('status').textContent, /Batch stopped after 1 imports/);
  assert.equal(f.app.getState().session.captures.length, 1);
  await f.get('upload').fire('click');
  assert.deepEqual(posts, ['c1', 'c2', 'c2']);
  assert.match(f.get('status').textContent, /Imported 1; verified and retained 1/);
});

test('revision conflict refreshes current metadata while preserving the edited patch bytes', async () => {
  let current = session(2);
  const f = await fixture((_path, opts) => opts.method === 'PATCH' ? (current = session(3), reply({ error: { message: 'Revision conflict' } }, 409)) : reply(current));
  await resume(f);
  const draft = '{"expected_revision":2,"calibration":{"sound_speed_m_s":340}}';
  f.get('patch').value = draft; await f.get('patch').fire('input'); await f.get('patch-apply').fire('click');
  assert.equal(f.get('patch').value, draft); assert.equal(f.app.getState().session.revision, 3);
  assert.match(f.get('status').textContent, /Revision conflict/);
  await f.get('patch-reset').fire('click'); assert.equal(JSON.parse(f.get('patch').value).expected_revision, 3);
});

test('lost start response retains exact request identity through retry and reload without automatic POST', async () => {
  const identities = [];
  const f = await fixture((_path, opts) => { if (opts.method === 'POST') { identities.push(JSON.parse(opts.body).request_id); throw new Error('Lost response'); } return reply(session()); });
  await resume(f); await f.get('run').fire('click');
  const pending = f.app.getState().pending;
  assert.ok(pending); assert.match(f.get('run').textContent, /Recover/); assert.equal(f.get('resume').disabled, true);
  await f.get('run').fire('click'); assert.deepEqual(identities, [pending, pending]);
  const restored = await fixture(() => reply(session()), f.location.hash);
  assert.equal(restored.app.getState().pending, pending);
  assert.equal(restored.calls.filter(c => c.opts.method === 'POST').length, 0);
  assert.ok(!f.location.hash.includes(config.token));
});

test('unknown job status keeps same job locked and explicit retry observes it without another start', async () => {
  let fail = true;
  const f = await fixture((path, opts) => {
    if (path === '/v1/sessions/session1') return reply(session());
    if (path.endsWith('/jobs')) return reply({ job_id: 'job1', session_id: 'session1', status: 'running' });
    if (fail) throw new Error('Offline');
    return reply({ job_id: 'job1', session_id: 'session1', status: 'cancelled', progress: .2 });
  });
  await resume(f); await f.get('run').fire('click'); await settle();
  assert.match(f.get('status').textContent, /state is unknown/); assert.equal(f.get('run').disabled, true);
  fail = false; await f.get('observe').fire('click'); await settle();
  assert.equal(f.app.getState().job.status, 'cancelled'); assert.equal(f.opened.length, 0);
  assert.match(f.get('status').textContent, /no new result/);
  assert.equal(f.calls.filter(c => c.path.endsWith('/jobs') && c.opts.method === 'POST').length, 1);
});

test('saved job lookup failures retain exact identities and lock mutations until explicit recovery', async () => {
  for (const bad of ['offline', null, { job_id: 'other_job', session_id: 'session1', status: 'cancelled' },
    { job_id: 'job1', session_id: 'other_session', status: 'cancelled' }, { job_id: 'job1', session_id: 'session1', status: 'invented' }]) {
    let recovered = false;
    const saved = '#session=session1&job=job1';
    const f = await fixture((path, opts) => {
      assert.notEqual(opts.method, 'POST', 'Restoration must never start or cancel processing');
      if (path === '/v1/sessions/session1') return reply(session());
      assert.equal(path, '/v1/jobs/job1');
      if (recovered) return reply({ job_id: 'job1', session_id: 'session1', status: 'cancelled' });
      if (bad === 'offline') throw new Error('Transient offline');
      return reply(bad);
    }, saved);
    assert.equal(f.location.hash, saved); assert.equal(f.app.getState().job, null);
    for (const name of ['run', 'create', 'upload', 'resume', 'patch-apply', 'export', 'import']) assert.equal(f.get(name).disabled, true, name);
    assert.equal(f.get('observe').disabled, false); assert.match(f.get('observe').textContent, /Retry saved workspace/);
    await f.get('run').fire('click'); assert.equal(f.calls.some(call => call.opts.method === 'POST'), false);
    recovered = true; await f.get('observe').fire('click'); await settle();
    assert.equal(f.app.getState().recovery, null); assert.equal(f.app.getState().job.job_id, 'job1');
    assert.equal(f.app.getState().job.status, 'cancelled'); assert.equal(f.get('run').disabled, false);
    assert.equal(f.location.hash, saved);
  }
});

test('failed saved-session lookup retains pending request without automatic processing', async () => {
  let recovered = false;
  const saved = '#session=session1&request=request_original';
  const f = await fixture((path, opts) => {
    assert.equal(path, '/v1/sessions/session1'); assert.notEqual(opts.method, 'POST');
    if (!recovered) throw new Error('Session unavailable');
    return reply(session());
  }, saved);
  assert.equal(f.location.hash, saved); assert.equal(f.get('run').disabled, true); assert.equal(f.get('create').disabled, true);
  recovered = true; await f.get('observe').fire('click'); await settle();
  assert.equal(f.app.getState().pending, 'request_original'); assert.match(f.get('run').textContent, /Recover processing start/);
  assert.equal(f.location.hash, saved); assert.equal(f.calls.some(call => call.opts.method === 'POST'), false);
});

test('wrong saved-session response cannot replace the requested identity', async () => {
  const saved = '#session=session1&job=job1';
  const f = await fixture(() => reply({ ...session(), session_id: 'session2' }), saved);
  assert.equal(f.app.getState().session, null); assert.equal(f.app.getState().job, null);
  assert.equal(f.location.hash, saved); assert.equal(f.get('run').disabled, true); assert.equal(f.get('observe').disabled, false);
  assert.equal(f.calls.some(call => call.path.includes('/v1/jobs/')), false);
});

test('completion preserves a newer manual inspection and opens exact immutable job result on request', async () => {
  let release;
  const pending = new Promise(resolve => { release = resolve; });
  const result = { session_id: 'session1', session_revision: 1, status: 'no_result' };
  const f = await fixture((path) => {
    if (path === '/v1/sessions/session1') return reply(session(2));
    if (path.endsWith('/jobs')) return reply({ job_id: 'job1', session_id: 'session1', status: 'running' });
    if (path.endsWith('/result')) return reply(result);
    return pending;
  });
  await resume(f); await f.get('run').fire('click'); f.manualImport();
  release(reply({ job_id: 'job1', session_id: 'session1', status: 'completed', progress: 1 })); await settle();
  assert.equal(f.opened.length, 0); assert.match(f.get('status').textContent, /current inspection was retained/);
  await f.get('show').fire('click'); assert.equal(f.opened.length, 1); assert.equal(f.opened[0].value.stale, true);
  assert.equal(f.calls.some(c => c.path.includes('latest')), false);
});

test('cancel response is observed on the same job and never creates an invented result', async () => {
  let polls = 0;
  const f = await fixture((path) => {
    if (path === '/v1/sessions/session1') return reply(session());
    if (path.endsWith('/jobs')) return reply({ job_id: 'job1', session_id: 'session1', status: 'running' });
    if (path.endsWith('/cancel')) return reply({ job_id: 'job1', session_id: 'session1', status: 'cancelled' });
    if (polls++ === 0) throw new Error('Offline');
    return reply({ job_id: 'job1', session_id: 'session1', status: 'cancelled' });
  });
  await resume(f); await f.get('run').fire('click'); await settle();
  await f.get('cancel').fire('click'); await settle();
  assert.equal(f.app.getState().job.status, 'cancelled'); assert.equal(f.opened.length, 0);
  assert.equal(f.calls.filter(c => c.path.endsWith('/cancel')).length, 1);
});

test('late cancellation response cannot attach an old job to a newly selected session', async () => {
  let releasePoll, releaseCancel;
  const poll = new Promise(resolve => { releasePoll = resolve; });
  const cancel = new Promise(resolve => { releaseCancel = resolve; });
  const terminal = { job_id: 'job1', session_id: 'session1', status: 'cancelled' };
  const f = await fixture((path) => {
    if (path === '/v1/sessions/session1') return reply(session());
    if (path === '/v1/sessions/session2') return reply({ ...session(), session_id: 'session2' });
    if (path.endsWith('/jobs')) return reply({ ...terminal, status: 'running' });
    if (path.endsWith('/cancel')) return cancel;
    return poll;
  });
  await resume(f); await f.get('run').fire('click');
  const cancelling = f.get('cancel').fire('click');
  releasePoll(reply(terminal)); await settle();
  assert.equal(f.get('resume').disabled, false);
  await resume(f, 'session2');
  releaseCancel(reply(terminal)); await cancelling; await settle();
  assert.equal(f.app.getState().session.session_id, 'session2');
  assert.equal(f.app.getState().job, null, 'Old cancellation response must not reattach its job after session selection');
});

test('late terminal-job refresh cannot replace a newer session selection', async () => {
  let releaseRefresh, reads = 0;
  const refreshed = new Promise(resolve => { releaseRefresh = resolve; });
  const f = await fixture((path) => {
    if (path === '/v1/sessions/session1') return reads++ === 0 ? reply(session()) : refreshed;
    if (path === '/v1/sessions/session2') return reply({ ...session(), session_id: 'session2' });
    if (path.endsWith('/jobs')) return reply({ job_id: 'job1', session_id: 'session1', status: 'running' });
    return reply({ job_id: 'job1', session_id: 'session1', status: 'failed', error: { message: 'No usable input' } });
  });
  await resume(f); await f.get('run').fire('click'); await settle();
  assert.equal(f.get('resume').disabled, true, 'Session selection stays locked until terminal refresh finishes');
  // Force the mocked handler to exercise the response guard independently of disabled UI.
  await resume(f, 'session2');
  releaseRefresh(reply(session(1))); await settle();
  assert.equal(f.app.getState().session.session_id, 'session2', 'Old job refresh must not restore its session after a new selection');
});

test('observer rejects unrelated or unknown job records and abort stops polling without cancellation', async () => {
  const f = await fixture();
  for (const value of [{ job_id: 'other', status: 'running' }, { job_id: 'job1', status: 'mystery' }]) {
    await assert.rejects(f.helpers.observeJob({ request: async () => value }, 'job1'), /Unexpected job status/);
  }
  const controller = new AbortController(), paths = [];
  await assert.rejects(f.helpers.observeJob({ request: async path => { paths.push(path); return { job_id: 'job1', status: 'running' }; } }, 'job1', {
    signal: controller.signal,
    onUpdate: () => controller.abort(),
  }), { name: 'AbortError' });
  assert.deepEqual(paths, ['/v1/jobs/job1']);
});

test('standalone result viewer never bootstraps or exposes local workspace', async () => {
  const context = vm.createContext({ TextEncoder, AbortSignal, AbortController, DOMException, URLSearchParams });
  const data = new vm.SourceTextModule(sources['workspace-data'], { context });
  const resultData = new vm.SourceTextModule(sources['result-data'], { context });
  const results = new vm.SyntheticModule(['getDisplayVersion', 'openBackendResult', 'markSessionRevision', 'getBackendResult', 'subscribeBackendResult'], function () { for (const n of ['getDisplayVersion', 'openBackendResult', 'markSessionRevision', 'getBackendResult', 'subscribeBackendResult']) this.setExport(n, () => {}); }, { context });
  const comparison = new vm.SourceTextModule(sources.comparison, { context });
  const module = new vm.SourceTextModule(sources.workspace, { context });
  await module.link(name => ({ './workspace-data.js': data, './results.js': results, './result-data.js': resultData, './comparison.js': comparison })[name]); await module.evaluate();
  let fetches = 0;
  const panel = { hidden: true };
  await module.namespace.initWorkspace({ querySelector: () => panel }, { pathname: '/results.html' }, {}, async () => { fetches++; });
  assert.equal(fetches, 0); assert.equal(panel.hidden, true);
});
