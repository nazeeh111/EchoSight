/** Local processing client. The transient UI token is kept only in memory. */
export const TERMINAL_JOBS = new Set(['completed', 'failed', 'cancelled', 'interrupted']);
const ID = /^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$/;
const object = value => value && typeof value === 'object' && !Array.isArray(value);
const encoder = new TextEncoder();
const SESSION_FIELDS = ['schema_version', 'session_id', 'coordinate_frame_id', 'source_position_m', 'source_position_std_m', 'sound_speed_m_s', 'sound_speed_std_m_s', 'source_clock_scale', 'source_clock_std_ppm', 'probe', 'effective_speed_m_s', 'source_effective_speed_covariance', 'interpretation_context'];
const CAPTURE_FIELDS = ['capture_id', 'receiver_position_m', 'receiver_position_std_m', 'provenance', 'device_id', 'receiver_pose_group_id', 'notes'];
export function requireId(value) { if (typeof value !== 'string' || !ID.test(value)) throw new Error('Use a valid session/job/capture ID (1–80 ASCII letters, digits, underscores or hyphens).'); return value; }
export function parseObject(text, maximum = 1024 * 1024) {
  if (encoder.encode(text).byteLength > maximum) throw new Error('JSON exceeds the metadata limit.');
  const value = JSON.parse(text);
  if (!object(value)) throw new Error('Use a JSON object.');
  return value;
}
export function splitDefinition(value) {
  if (!object(value)) throw new Error('Session definition must be an object.');
  const session = Object.fromEntries(SESSION_FIELDS.filter(key => key in value).map(key => [key, value[key]]));
  const plan = value.captures ?? [];
  if (!Array.isArray(plan) || plan.length > 32) throw new Error('At most 32 captures are supported.');
  session.captures = [];
  return { session, plan, ignored: Object.keys(value).filter(key => !SESSION_FIELDS.includes(key) && key !== 'captures') };
}
export function captureMetadata(capture) {
  if (!object(capture)) throw new Error('Each capture plan entry must be an object.');
  requireId(capture.capture_id);
  if (!['measured', 'simulated', 'replayed', 'supplied'].includes(capture.provenance)) throw new Error(`Declare provenance for ${capture.capture_id}; it is not inferred from the filename.`);
  if (capture.receiver_position_m != null && (!Array.isArray(capture.receiver_position_m) || capture.receiver_position_m.length !== 3 || !capture.receiver_position_m.every(n => typeof n === 'number' && Number.isFinite(n) && Math.abs(n) <= 1000))) throw new Error(`Invalid receiver position for ${capture.capture_id}.`);
  if (capture.receiver_position_std_m !== undefined && (typeof capture.receiver_position_std_m !== 'number' || !Number.isFinite(capture.receiver_position_std_m) || capture.receiver_position_std_m < 0 || capture.receiver_position_std_m > 10)) throw new Error('Receiver uncertainty must be between 0 and 10 metres.');
  return Object.fromEntries(CAPTURE_FIELDS.filter(key => key in capture).map(key => [key, capture[key]]));
}
export function asciiJSON(value) {
  return JSON.stringify(value).replace(/[^\x00-\x7f]/g, character => '\\u' + character.charCodeAt(0).toString(16).padStart(4, '0'));
}
export function planUploads(plan, files, recordingLimit = 64 * 1024 * 1024) {
  if (!Array.isArray(plan) || !plan.length || plan.length > 32) throw new Error('Supply a capture plan with 1–32 entries.');
  const byName = new Map(), ids = new Set(), used = new Set();
  for (const file of files) {
    if (byName.has(file.name)) throw new Error('Selected files have duplicate basenames. Rename them or upload separately.');
    if (!file.size || file.size > recordingLimit) throw new Error(`${file.name} exceeds the recording limit or is empty.`);
    byName.set(file.name, file);
  }
  const uploads = plan.map(capture => {
    const metadata = captureMetadata(capture);
    if (ids.has(metadata.capture_id)) throw new Error('Capture IDs must be unique.'); ids.add(metadata.capture_id);
    if (typeof capture.recording_path !== 'string') throw new Error(`recording_path is required for ${metadata.capture_id}. It identifies a selected file, not a server path.`);
    const name = capture.recording_path.replaceAll('\\', '/').split('/').at(-1);
    if (!name || used.has(name)) throw new Error('Each capture must identify a different selected filename.'); used.add(name);
    const file = byName.get(name);
    if (!file) throw new Error(`Choose the original file ${name} for ${metadata.capture_id}.`);
    if (capture.sha256 !== undefined && !/^[a-f0-9]{64}$/.test(capture.sha256)) throw new Error('Expected recording SHA-256 must be 64 lowercase hex characters.');
    const header = asciiJSON(metadata);
    if (header.length > 8192) throw new Error(`Capture metadata for ${metadata.capture_id} exceeds the 8 KiB header limit.`);
    return { file, metadata, header, expected: capture.sha256 };
  });
  if (files.length !== uploads.length) throw new Error('Select exactly the recordings listed in the plan; extra files are not silently ignored.');
  if (files.reduce((sum, file) => sum + file.size, 0) > 256 * 1024 * 1024) throw new Error('Selected recordings exceed the 256 MiB session byte limit.');
  return uploads;
}
export async function sha256(bytes, cryptoAPI = globalThis.crypto) {
  return [...new Uint8Array(await cryptoAPI.subtle.digest('SHA-256', bytes))].map(n => n.toString(16).padStart(2, '0')).join('');
}
export class WorkspaceClient {
  constructor(config, fetcher = globalThis.fetch.bind(globalThis)) { this.token = config.token; this.limits = config.limits; this.fetcher = fetcher; }
  async request(path, { method = 'GET', json, bytes, headers = {}, binary = false, signal } = {}) {
    if (!path.startsWith('/v1/') || path.includes('?') || path.includes('#')) throw new Error('Only local versioned API paths are supported.');
    let body = bytes;
    if (json !== undefined) { body = JSON.stringify(json); headers = { ...headers, 'Content-Type': 'application/json' }; }
    const response = await this.fetcher(path, {
      method, body, headers: { ...headers, 'X-EchoSight-UI-Token': this.token },
      mode: 'same-origin', credentials: 'omit', redirect: 'error', cache: 'no-store',
      signal: signal ?? AbortSignal.timeout(120000),
    });
    if (binary && response.ok) {
      const blob = await response.blob();
      if (blob.size > this.limits.archive_bytes) throw new Error('Archive exceeds the local transfer limit.');
      return blob;
    }
    const raw = await response.text();
    if (encoder.encode(raw).byteLength > 32 * 1024 * 1024) throw new Error('API response exceeds the result limit.');
    let value;
    try { value = JSON.parse(raw); } catch { throw new Error('The local API returned an unreadable response.'); }
    if (!response.ok) {
      const error = new Error(typeof value.error?.message === 'string' ? value.error.message : `Local API request failed (${response.status}).`);
      error.status = response.status; throw error;
    }
    return value;
  }
  async upload(sid, entry, existing) {
    const bytes = await entry.file.arrayBuffer(), digest = await sha256(bytes);
    if (entry.expected && entry.expected !== digest) throw new Error(`Checksum differs for ${entry.file.name}. No upload performed for this capture.`);
    if (existing) {
      if (existing.sha256 !== digest) throw new Error(`Capture ${existing.capture_id} already stores different bytes; original recording IDs cannot be overwritten.`);
      const supplied = captureMetadata(entry.metadata);
      for (const key of Object.keys(supplied)) if (JSON.stringify(supplied[key]) !== JSON.stringify(existing[key])) throw new Error(`Stored metadata differs for ${existing.capture_id}; use a revision-checked calibration patch instead.`);
      return { skipped: true, capture: existing };
    }
    const capture = await this.request(`/v1/sessions/${requireId(sid)}/recordings`, {
      method: 'POST', bytes, headers: { 'Content-Type': 'application/octet-stream', 'X-Capture-Metadata': entry.header, 'X-Recording-SHA256': digest },
    });
    return { skipped: false, capture };
  }
}
export const sleep = (ms, signal) => new Promise((resolve, reject) => {
  if (signal?.aborted) { reject(new DOMException('Observation stopped', 'AbortError')); return; }
  const abort = () => { clearTimeout(timer); reject(new DOMException('Observation stopped', 'AbortError')); };
  const timer = setTimeout(() => { signal?.removeEventListener('abort', abort); resolve(); }, ms);
  signal?.addEventListener('abort', abort, { once: true });
});
export async function observeJob(client, id, { onUpdate = () => {}, signal, delay = sleep, intervalMs = 750 } = {}) {
  requireId(id);
  for (;;) {
    const job = await client.request(`/v1/jobs/${id}`, { signal });
    validateJob(job, id);
    onUpdate(job);
    if (TERMINAL_JOBS.has(job.status)) return job;
    await delay(intervalMs, signal);
  }
}
export function validateJob(job, id) {
  if (!job || job.job_id !== id || !['queued', 'running', ...TERMINAL_JOBS].includes(job.status)) throw new Error('Unexpected job status response; processing state is unknown.');
  return job;
}
