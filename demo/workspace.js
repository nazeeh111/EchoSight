/** Opt-in same-origin workspace. Original recordings remain in the local store. */
import { WorkspaceClient, TERMINAL_JOBS, requireId, parseObject, splitDefinition, planUploads, observeJob, validateJob } from './workspace-data.js';
import { getDisplayVersion, openBackendResult, markSessionRevision, getBackendResult, subscribeBackendResult } from './results.js';
import { initComparison } from './comparison.js';
import { displayText } from './result-data.js';

export async function initWorkspace(document, location, history, fetcher = globalThis.fetch.bind(globalThis)) {
  const panel = document.querySelector('#workspace-panel');
  if (!panel || !location.pathname.startsWith('/ui/')) return;
  const el = name => document.querySelector(`#workspace-${name}`);
  const status = text => { el('status').textContent = text; };
  let config;
  try {
    const response = await fetcher('/ui/config', { mode: 'same-origin', credentials: 'omit', redirect: 'error', cache: 'no-store', signal: AbortSignal.timeout(10000) });
    if (!response.ok) throw new Error('Workspace bootstrap failed.');
    config = await response.json();
    if (config.enabled !== true || typeof config.token !== 'string' || config.token.length < 32 || !['recording_bytes', 'archive_bytes', 'json_bytes'].every(k => Number.isSafeInteger(config.limits?.[k]) && config.limits[k] > 0)) throw new Error('Invalid local workspace configuration.');
  } catch (error) { el('launch').hidden = false; el('launch').open = true; return; }
  const client = new WorkspaceClient(config, fetcher);
  panel.hidden = false; el('launch').hidden = true;
  initComparison(document, client, { getResult: getBackendResult, subscribe: subscribeBackendResult });
  let session = null, job = null, busy = false, monitor = null, pending = null, cached = null, displayVersion = null, patchDirty = false, generation = 0, recovery = null;
  const active = () => Boolean(pending || (job && !TERMINAL_JOBS.has(job.status)));
  function remember() {
    if (recovery) return; // Preserve the original recovery address until every identity is verified.
    const hash = new URLSearchParams();
    if (session) hash.set('session', session.session_id);
    if (job) hash.set('job', job.job_id);
    if (pending) hash.set('request', pending);
    history.replaceState(null, '', `${location.pathname}#${hash}`);
  }
  function controls() {
    const locked = busy || Boolean(recovery) || active() || Boolean(monitor);
    for (const name of ['create', 'resume', 'definition', 'spec', 'resume-id', 'upload', 'plan', 'recordings', 'patch-reset', 'patch-apply', 'archive', 'import']) el(name).disabled = locked || (['upload', 'patch-reset', 'patch-apply'].includes(name) && !session);
    el('run').disabled = busy || Boolean(recovery) || Boolean(monitor) || !session || Boolean(job && !TERMINAL_JOBS.has(job.status));
    el('run').textContent = pending ? 'Recover processing start' : 'Process session';
    el('cancel').disabled = Boolean(recovery) || !job || TERMINAL_JOBS.has(job.status);
    el('observe').disabled = busy || (!recovery && !job) || Boolean(monitor);
    el('observe').textContent = recovery ? 'Retry saved workspace' : 'Retry job status';
    el('show').disabled = busy || Boolean(recovery) || job?.status !== 'completed';
    el('export').disabled = locked || !session;
    el('session-label').textContent = session ? `${session.session_id} · revision ${session.revision} · ${session.captures.length} recordings` : 'No session selected';
  }
  function patchTemplate() {
    el('patch').value = JSON.stringify({ expected_revision: session.revision, calibration: {}, captures: [] }, null, 2); patchDirty = false;
  }
  function showSession(value) {
    requireId(value.session_id);
    if (!Number.isInteger(value.revision) || !Array.isArray(value.captures)) throw new Error('Invalid session response.');
    session = value; el('resume-id').value = value.session_id;
    el('session-data').textContent = displayText(value);
    if (!patchDirty) patchTemplate();
    markSessionRevision(value); remember(); controls();
  }
  async function refresh() {
    const sid = session.session_id, version = generation;
    const value = await client.request(`/v1/sessions/${requireId(sid)}`);
    if (version !== generation || session?.session_id !== sid) return false;
    showSession(value); return true;
  }
  function chooseSession(value) { generation++; job = null; pending = null; cached = null; displayVersion = null; patchDirty = false; showSession(value); }
  function jobLabel(value) {
    job = value;
    const p = typeof value.progress === 'number' && Number.isFinite(value.progress) ? Math.max(0, Math.min(1, value.progress)) : 0;
    el('progress').value = p;
    el('job-label').textContent = `${value.job_id}: ${value.status} · ${Math.round(p * 100)}% work completed, not confidence.${value.error ? ' ' + displayText(value.error) : ''}`;
    remember(); controls();
  }
  async function loadCompleted(open = false) {
    const id = job.job_id, sid = session.session_id, version = generation;
    const [value, current] = await Promise.all([client.request(`/v1/jobs/${id}/result`), client.request(`/v1/sessions/${sid}`)]);
    if (version !== generation || id !== job?.job_id || sid !== session?.session_id) return;
    if (value.session_id !== sid) throw new Error('Job result belongs to a different session.');
    cached = { ...value, stale: value.session_revision !== current.revision }; showSession(current);
    if (open || (displayVersion !== null && getDisplayVersion() === displayVersion)) {
      openBackendResult(cached, `Local job ${id}`); displayVersion = getDisplayVersion();
      status(`Completed result opened${cached.stale ? '; session has a newer revision and this result is stale' : ''}.`);
    } else status('Processing completed. View its result when ready; your current inspection was retained.');
  }
  async function observe() {
    if (!job || monitor) return;
    const controller = new AbortController(), version = generation, id = job.job_id;
    monitor = controller; controls();
    try {
      const value = await observeJob(client, job.job_id, { signal: controller.signal, onUpdate(value) {
        if (value.session_id !== session.session_id) throw new Error('Job belongs to a different session.');
        jobLabel(value);
      }});
      if (value.status === 'completed') await loadCompleted();
      else { if (await refresh() && version === generation && id === job?.job_id) status(`${value.status}: no new result was published. Original recordings are retained.${value.error ? ' ' + displayText(value.error) : ''}`); }
    } catch (error) {
      if (!controller.signal.aborted && version === generation && id === job?.job_id) status(`Job state is unknown: ${error.message} Retry status for this same job; do not start another run.`);
    } finally { if (monitor === controller) monitor = null; controls(); }
  }
  async function action(fn) {
    if (busy || recovery) return;
    busy = true; controls();
    try { await fn(); } catch (error) { status(error.message); }
    finally { busy = false; controls(); }
  }
  el('patch').addEventListener('input', () => { patchDirty = true; });
  el('definition').addEventListener('change', () => action(async () => {
    const file = el('definition').files?.[0]; if (!file) return;
    if (file.size > config.limits.json_bytes) throw new Error('Definition exceeds the metadata limit.');
    const { session: spec, plan, ignored } = splitDefinition(parseObject(await file.text(), config.limits.json_bytes));
    el('spec').value = JSON.stringify(spec, null, 2); el('plan').value = JSON.stringify(plan, null, 2);
    status(`Definition loaded for review; no files uploaded.${ignored.length ? ' Computed or unsupported top-level fields omitted: ' + ignored.join(', ') : ''}`);
  }));
  el('create').addEventListener('click', () => action(async () => {
    const { session: spec, plan, ignored } = splitDefinition(parseObject(el('spec').value, config.limits.json_bytes));
    if (plan.length) el('plan').value = JSON.stringify(plan, null, 2);
    chooseSession(await client.request('/v1/sessions', { method: 'POST', json: spec }));
    status(`Session created. Review the capture plan and import its original files.${ignored.length ? ' Unsupported fields omitted: ' + ignored.join(', ') : ''}`);
  }));
  el('resume').addEventListener('click', () => action(async () => {
    const id = requireId(el('resume-id').value.trim());
    const value = await client.request(`/v1/sessions/${id}`);
    if (session?.session_id === id) showSession(value); else chooseSession(value);
    status('Session loaded. Raw recordings and supplied calibration shown below.');
  }));
  el('upload').addEventListener('click', () => action(async () => {
    if (new TextEncoder().encode(el('plan').value).byteLength > config.limits.json_bytes) throw new Error('Capture plan exceeds the metadata limit.');
    const entries = planUploads(JSON.parse(el('plan').value), Array.from(el('recordings').files), config.limits.recording_bytes);
    await refresh(); let added = 0, skipped = 0;
    try {
      for (const entry of entries) {
        status(`Checking/importing ${entry.file.name} (${added + skipped + 1}/${entries.length})…`);
        const result = await client.upload(session.session_id, entry, session.captures.find(c => c.capture_id === entry.metadata.capture_id));
        if (result.skipped) skipped++; else { added++; session.captures.push(result.capture); }
      }
      status(`Imported ${added}; verified and retained ${skipped} already stored recordings.`);
    } catch (error) { status(`Batch stopped after ${added} imports and ${skipped} verified existing recordings. Stored files remain available. ${error.message}`); }
    finally { await refresh(); }
  }));
  el('patch-reset').addEventListener('click', () => { if (session && !active() && !busy) { patchTemplate(); status('New patch template uses the loaded revision. Review before applying.'); } });
  el('patch-apply').addEventListener('click', () => action(async () => {
    const patch = parseObject(el('patch').value, config.limits.json_bytes);
    try { const value = await client.request(`/v1/sessions/${session.session_id}`, { method: 'PATCH', json: patch }); patchDirty = false; showSession(value); status('Calibration saved. Reprocess for a result at this revision.'); }
    catch (error) { if (error.status === 409) await refresh(); throw error; }
  }));
  el('run').addEventListener('click', () => action(async () => {
    if (job && !TERMINAL_JOBS.has(job.status)) return;
    if (!pending) { pending = 'request_' + crypto.randomUUID().replaceAll('-', ''); displayVersion = getDisplayVersion(); job = null; cached = null; remember(); }
    status('Starting processing. The request identity is retained if the response is lost.');
    try {
      const value = await client.request(`/v1/sessions/${session.session_id}/jobs`, { method: 'POST', json: { request_id: pending } });
      if (value.session_id !== session.session_id) throw new Error('Job response belongs to another session.');
      requireId(value.job_id); pending = null; jobLabel(value); void observe();
    } catch (error) { status(`Processing start is unconfirmed: ${error.message} Use Recover processing start to retry the same request safely.`); }
  }));
  el('observe').addEventListener('click', () => { if (recovery) void restoreSaved(); else void observe(); });
  el('cancel').addEventListener('click', async () => {
    if (!job || TERMINAL_JOBS.has(job.status)) return;
    const id = job.job_id, sid = session.session_id, version = generation;
    const current = () => version === generation && id === job?.job_id && sid === session?.session_id;
    el('cancel').disabled = true;
    try {
      const value = await client.request(`/v1/jobs/${id}/cancel`, { method: 'POST', json: {} });
      if (!current()) return;
      if (value.job_id !== id || value.session_id !== sid) throw new Error('Unexpected cancellation response identity.');
      if (!TERMINAL_JOBS.has(job.status)) jobLabel(value);
      status(TERMINAL_JOBS.has(job.status) ? `Job is ${job.status}.` : 'Cancellation requested. Wait for the terminal job state; previous inspected results remain visible.');
      if (!monitor) void observe();
    }
    catch (error) { if (current()) status(`Cancellation is unconfirmed: ${error.message} Retry cancellation or job status for this job.`); }
    finally { controls(); }
  });
  el('show').addEventListener('click', () => action(async () => { await loadCompleted(true); }));
  el('export').addEventListener('click', () => action(async () => {
    const blob = await client.request(`/v1/sessions/${session.session_id}/export`, { binary: true });
    const url = URL.createObjectURL(blob), link = document.createElement('a');
    link.href = url; link.download = `${session.session_id}.zip`; document.body.append(link); link.click(); link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000); status('Archive downloaded with original recordings. Archived calculations are quarantined when imported.');
  }));
  el('import').addEventListener('click', () => action(async () => {
    const file = el('archive').files?.[0]; if (!file) throw new Error('Choose an exported raw archive first.');
    if (!file.size || file.size > config.limits.archive_bytes) throw new Error('Archive is empty or exceeds the transfer limit.');
    chooseSession(await client.request('/v1/imports', { method: 'POST', bytes: await file.arrayBuffer(), headers: { 'Content-Type': 'application/zip' } }));
    status('Archive imported. Reprocess retained recordings; archived calculations remain quarantined.');
  }));
  globalThis.addEventListener?.('pagehide', () => monitor?.abort(), { once: true });
  controls();
  async function restoreSaved() {
    if (!recovery || busy) return;
    busy = true; controls();
    try {
      const value = await client.request(`/v1/sessions/${recovery.session}`);
      if (value.session_id !== recovery.session) throw new Error('Saved session response has a different identity.');
      chooseSession(value);
      if (recovery.job) {
        const value = validateJob(await client.request(`/v1/jobs/${recovery.job}`), recovery.job);
        if (value.session_id !== recovery.session) throw new Error('Saved job does not belong to this session.');
        jobLabel(value);
      } else if (recovery.request) pending = recovery.request;
      recovery = null; remember();
      if (job) void observe();
      else status(pending ? 'A processing start was unconfirmed before reload. Recover the same request to learn its state.' : 'Saved session restored.');
    } catch (error) {
      status(`Saved processing state is unknown: ${error.message} Retry saved workspace to recover the same identities. The original address is retained; no new processing will start.`);
    } finally { busy = false; controls(); }
  }
  try {
    const saved = new URLSearchParams(location.hash.slice(1));
    if (saved.has('session')) {
      recovery = { session: requireId(saved.get('session')), job: saved.has('job') ? requireId(saved.get('job')) : null,
        request: saved.has('request') ? requireId(saved.get('request')) : null };
      await restoreSaved();
    }
  } catch (error) { status(`Saved workspace could not be restored: ${error.message}`); }
  return { client, getState: () => ({ session, job, pending, busy, recovery }), observe };
}
if (typeof document !== 'undefined') void initWorkspace(document, location, history);
