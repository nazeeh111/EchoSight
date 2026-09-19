"""Bounded, atomic local storage. Raw inputs are immutable and retained verbatim."""
from __future__ import annotations

import copy
import csv
from array import array
import hashlib
import fcntl
import io
import json
import math
import os
import re
import shutil
import tempfile
import threading
import time
import uuid
import wave
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

SCHEMA_VERSION = '1.0'
MAX_RECORDING_BYTES = 64 * 1024 * 1024
MAX_ARCHIVE_BYTES = 256 * 1024 * 1024
MAX_CAPTURES = 32
MAX_SECONDS = 120
MAX_JSON_BYTES = 1024 * 1024
_ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$')
TERMINAL = {'completed', 'failed', 'cancelled', 'interrupted'}


def _id(value):
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise ValueError('invalid identifier')
    return value


def _number(value, name, low, high):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f'{name} must be finite and in [{low}, {high}]')
    return value


def _position(value, name):
    if not isinstance(value, list) or len(value) != 3:
        raise ValueError(f'{name} must be a three-element list in metres')
    for item in value: _number(item, name, -1000, 1000)


def validate_session(spec):
    """Validate physical values; absent calibration remains absent for diagnostics."""
    if not isinstance(spec, dict): raise ValueError('session must be an object')
    try:
        encoded = json.dumps(spec, allow_nan=False)
    except (ValueError, TypeError) as exc:
        raise ValueError('session must contain finite JSON values') from exc
    if len(encoded.encode()) > MAX_JSON_BYTES: raise ValueError('session metadata too large')
    s = copy.deepcopy(spec)
    if s.get('schema_version', SCHEMA_VERSION) != SCHEMA_VERSION: raise ValueError('unsupported schema_version')
    s.setdefault('schema_version', SCHEMA_VERSION)
    if 'session_id' in s: _id(s['session_id'])
    for key, default, low, high in (
        ('sound_speed_m_s',343.,250,450), ('sound_speed_std_m_s',.6,0,30),
        ('source_clock_scale',1.,.98,1.02), ('source_clock_std_ppm',100.,0,20000),
        ('source_position_std_m',.01,0,10)):
        s.setdefault(key, default); _number(s[key], key, low, high)
    if s.get('source_position_m') is not None: _position(s['source_position_m'], 'source_position_m')
    captures = s.setdefault('captures', [])
    if not isinstance(captures, list) or len(captures) > MAX_CAPTURES: raise ValueError('captures must be a list of at most 32 captures')
    seen = set()
    for cap in captures:
        if not isinstance(cap, dict): raise ValueError('capture must be an object')
        cid = _id(cap.get('capture_id'))
        if cid in seen: raise ValueError('duplicate capture_id')
        seen.add(cid)
        if cap.get('receiver_position_m') is not None: _position(cap['receiver_position_m'], 'receiver_position_m')
        cap.setdefault('receiver_position_std_m', .01)
        _number(cap['receiver_position_std_m'], 'receiver_position_std_m', 0, 10)
        cap.setdefault('provenance', 'measured')
        if cap['provenance'] not in {'measured', 'simulated', 'replayed', 'supplied'}: raise ValueError('invalid recording provenance')
        if 'sample_rate_hz' in cap: _number(cap['sample_rate_hz'], 'sample_rate_hz', 8000, 192000)
        if 'recording_path' in cap and not isinstance(cap['recording_path'], str): raise ValueError('recording_path must be a string')
    if 'probe' in s and not isinstance(s['probe'], dict): raise ValueError('probe must be an object')
    return s


def load_session(path):
    """Trusted local CLI loader; relative recording paths resolve beside JSON."""
    path = Path(path)
    if path.stat().st_size > MAX_JSON_BYTES: raise ValueError('session metadata too large')
    s = validate_session(json.loads(path.read_text()))
    for cap in s['captures']:
        if cap.get('recording_path'):
            cap['recording_path'] = str((path.parent / cap['recording_path']).resolve())
    return s


def _read_wav(path):
    try:
        with wave.open(str(path), 'rb') as f:
            channels, width, rate, frames = f.getnchannels(), f.getsampwidth(), f.getframerate(), f.getnframes()
            if channels != 1 or width not in (1, 2, 3, 4) or f.getcomptype() != 'NONE':
                raise ValueError('recording must be uncompressed mono PCM WAV (8/16/24/32 bit)')
            if not 8000 <= rate <= 192000 or not 1 <= frames <= rate * MAX_SECONDS:
                raise ValueError('recording rate/duration outside limits: 8–192 kHz, 0–120 s')
            data = f.readframes(frames)
            if len(data) != frames * width: raise ValueError('truncated WAV payload')
    except (wave.Error, EOFError) as exc:
        raise ValueError('invalid PCM WAV') from exc
    if width == 1: samples = (np.frombuffer(data, dtype=np.uint8).astype(np.float64) - 128) / 128
    elif width == 2: samples = np.frombuffer(data, dtype='<i2').astype(np.float64) / 32768
    elif width == 4: samples = np.frombuffer(data, dtype='<i4').astype(np.float64) / 2147483648
    else:
        b = np.frombuffer(data, dtype=np.uint8).reshape(-1, 3).astype(np.int32)
        values = b[:, 0] | b[:, 1] << 8 | b[:, 2] << 16
        values = (values ^ 0x800000) - 0x800000
        samples = values.astype(np.float64) / 8388608
    return samples, rate


def _csv_column(raw, field):
    try:
        text = raw.decode('utf-8-sig')
        first = text.split('\n', 1)[0]
        delimiter = ';' if ';' in first else ','
        rows = csv.reader(io.StringIO(text), delimiter=delimiter)
        header = next(rows)
        names = [name.strip() for name in header]
        if field not in names: return None
        if names.count(field) != 1: raise ValueError('duplicate CSV field')
        index = names.index(field); values = array('d')
        for row in rows:
            if not row or all(not item.strip() for item in row): continue
            if len(row) != len(header): raise ValueError('ragged CSV row')
            value = float(row[index])
            if not math.isfinite(value): raise ValueError('nonfinite CSV sample')
            values.append(value)
        return np.frombuffer(values, dtype=np.float64).copy()
    except (UnicodeError, csv.Error, StopIteration, OverflowError) as exc:
        raise ValueError('invalid phyphox CSV') from exc


def _read_phyphox(path):
    """Static fixture contract, not a claim of verified iPhone exports.

    Read exact sample_value and reported_rate_Hz CSV columns wherever named.
    Preserve original ZIP; decimal sample values are parsed directly to float64.
    """
    try:
        with zipfile.ZipFile(path) as z:
            infos = z.infolist()
            if len(infos) > 32 or len({i.filename for i in infos}) != len(infos): raise ValueError('too many or duplicate phyphox ZIP members')
            if sum(i.file_size for i in infos) > MAX_RECORDING_BYTES: raise ValueError('phyphox expanded bytes exceed limit')
            samples = None; rates = None
            for info in infos:
                if info.flag_bits & 1 or info.filename.startswith('/') or '..' in Path(info.filename).parts or '\\' in info.filename:
                    raise ValueError('unsafe phyphox ZIP member')
                if not info.filename.lower().endswith('.csv'): continue
                raw = z.read(info)
                x = _csv_column(raw, 'sample_value')
                r = _csv_column(raw, 'reported_rate_Hz')
                if x is not None:
                    if samples is not None: raise ValueError('multiple audio sample columns')
                    samples = x
                if r is not None:
                    if rates is not None: raise ValueError('multiple rate columns')
                    rates = r
            if samples is None or rates is None or len(rates) == 0:
                raise ValueError('phyphox ZIP requires sample_value and reported_rate_Hz columns')
            rate = float(rates[0])
            if rate != round(rate) or not 8000 <= rate <= 192000 or not np.all(rates == rate): raise ValueError('invalid or changing reported sample rate')
            if not 1 <= len(samples) <= rate * MAX_SECONDS: raise ValueError('phyphox sample duration outside limits')
            if np.max(np.abs(samples)) > 1: raise ValueError('phyphox raw audio must use normalized sample values in [-1, 1]')
            return samples, int(rate)
    except (zipfile.BadZipFile, RuntimeError) as exc:
        raise ValueError('invalid phyphox ZIP') from exc


def _is_zip(path):
    with open(path, 'rb') as stream: return stream.read(4) == b'PK\x03\x04'


def read_recording(path):
    path = Path(path)
    if not path.is_file() or path.stat().st_size > MAX_RECORDING_BYTES: raise ValueError('recording missing or exceeds 64 MiB')
    return _read_phyphox(path) if _is_zip(path) else _read_wav(path)


def import_recording(path, destination_dir):
    """Validate before storing; address original bytes by their content hash."""
    path = Path(path)
    samples, rate = read_recording(path)
    raw = path.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    dest = Path(destination_dir); dest.mkdir(parents=True, exist_ok=True)
    is_zip = _is_zip(path)
    target = dest / (sha + ('.zip' if is_zip else '.wav'))
    if not target.exists(): _atomic_bytes(target, raw)
    return {'recording_path': str(target.resolve()), 'sha256': sha, 'sample_rate_hz': rate,
            'sample_count': len(samples), 'duration_s': len(samples) / rate,
            'byte_count': len(raw), 'format': 'phyphox_csv_zip' if is_zip else 'pcm_wav', 'channels': 1,
            'diagnostics': ['sample_grid_unverified', 'phone_export_not_hardware_validated'] if is_zip else []}


def _atomic_bytes(path, content):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.writing-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(content); stream.flush(); os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)


def _write_json(path, data):
    _atomic_bytes(path, (json.dumps(data, indent=2, allow_nan=False) + '\n').encode())


class SessionStore:
    """Single-process store with two workers and at most eight unfinished jobs.

    One SessionStore owns one root. Do not run multiple server processes on it.
    Session snapshots and recording hashes make every job reproducible.
    """
    def __init__(self, root, max_workers=2, max_jobs=8):
        self.root = Path(root).resolve(); self.root.mkdir(parents=True, exist_ok=True)
        (self.root / 'sessions').mkdir(exist_ok=True); (self.root / 'jobs').mkdir(exist_ok=True)
        self._ownership_file = open(self.root / '.store.lock', 'a+b')
        try:
            fcntl.flock(self._ownership_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            self._ownership_file.close()
            raise RuntimeError('store already open by another process') from exc
        self._lock = threading.RLock(); self._events = {}; self._closed = False
        self._max_jobs = max_jobs
        self._pool = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix='echosight')
        for p in (self.root / 'jobs').glob('*.json'):
            if not re.fullmatch(r'job_[a-f0-9]{32}\.json', p.name): continue
            try: job = json.loads(p.read_text())
            except (ValueError, OSError): continue
            if job.get('status') not in TERMINAL:
                job.update(status='interrupted', error={'code': 'process_interrupted', 'message': 'Restart detected. Raw recordings retained; start a new job.'}, updated_at=time.time())
                _write_json(p, job)
    def __enter__(self): return self
    def __exit__(self, *args): self.close()
    def close(self):
        with self._lock:
            self._closed = True
            for event in self._events.values(): event.set()
        self._pool.shutdown(wait=True, cancel_futures=False)
        self._ownership_file.close()
    def _session_dir(self, sid): return self.root / 'sessions' / _id(sid)
    def _job_path(self, jid): return self.root / 'jobs' / (_id(jid) + '.json')
    def _raw_session(self, sid):
        p = self._session_dir(sid) / 'session.json'
        if not p.exists(): raise KeyError('session not found')
        return json.loads(p.read_text())
    def create_session(self, spec):
        s = validate_session(spec)
        if any('recording_path' in cap for cap in s['captures']): raise ValueError('upload raw recordings; external recording paths are forbidden')
        # Only upload commits capture entries, avoiding phantom recording references.
        if s['captures']: raise ValueError('create sessions with no captures; supply each capture with its recording')
        s.setdefault('session_id', 'session_' + uuid.uuid4().hex)
        s['created_at'] = time.time(); s['revision'] = 0
        with self._lock:
            d = self._session_dir(s['session_id'])
            if d.exists(): raise FileExistsError('session already exists')
            d.mkdir(); _write_json(d / 'session.json', s)
        return copy.deepcopy(s)
    def get_session(self, sid):
        with self._lock: s = self._raw_session(sid)
        for cap in s['captures']:
            p = (self._session_dir(sid) / cap['recording_path']).resolve()
            if not p.is_relative_to(self._session_dir(sid)): raise ValueError('recording path escapes session')
            cap['recording_path'] = str(p)
        return s
    def public_session(self, sid):
        """No server filesystem paths leave the HTTP interface."""
        with self._lock: return self._raw_session(sid)
    def add_recording(self, sid, path, metadata):
        allowed = {'capture_id', 'receiver_position_m', 'receiver_position_std_m', 'provenance', 'device_id', 'notes'}
        if not isinstance(metadata, dict) or set(metadata) - allowed: raise ValueError('unsupported capture metadata fields')
        cap = dict(metadata); cap.setdefault('capture_id', 'capture_' + uuid.uuid4().hex)
        validate_session({'captures': [cap]})
        with self._lock:
            s = self._raw_session(sid)
            if len(s['captures']) >= MAX_CAPTURES: raise ValueError('capture limit reached')
            if any(c['capture_id'] == cap['capture_id'] for c in s['captures']): raise FileExistsError('capture already exists')
            if sum(c.get('byte_count', 0) for c in s['captures']) + Path(path).stat().st_size > MAX_ARCHIVE_BYTES:
                raise ValueError('session recording byte limit reached')
            meta = import_recording(path, self._session_dir(sid) / 'raw')
            cap.update(meta); cap['recording_path'] = str(Path(meta['recording_path']).relative_to(self._session_dir(sid)))
            s['captures'].append(cap); s = validate_session(s); s['revision'] += 1
            _write_json(self._session_dir(sid) / 'session.json', s)
            return copy.deepcopy(s['captures'][-1])
    def start_job(self, sid, processor):
        with self._lock:
            if self._closed: raise RuntimeError('store is closed')
            if len(self._events) >= self._max_jobs: raise RuntimeError('job queue full')
            session = self.get_session(sid)
            # Serialize processing per session to prevent older results replacing newer ones.
            for jid in self._events:
                if self.get_job(jid)['session_id'] == sid: raise RuntimeError('session already has an active job')
            jid = 'job_' + uuid.uuid4().hex
            job = {'schema_version': SCHEMA_VERSION, 'job_id': jid, 'session_id': sid,
                   'session_revision': session['revision'], 'status': 'queued', 'progress': 0.,
                   'created_at': time.time(), 'updated_at': time.time()}
            _write_json(self._job_path(jid), job)
            _write_json(self.root / 'jobs' / (jid + '.input.json'), self._raw_session(sid))
            event = threading.Event(); self._events[jid] = event
            self._pool.submit(self._run, jid, session, processor, event)
            return copy.deepcopy(job)
    def _update_job(self, jid, **updates):
        with self._lock:
            job = self.get_job(jid); job.update(updates, updated_at=time.time()); _write_json(self._job_path(jid), job)
    def _run(self, jid, session, processor, event):
        try:
            if event.is_set(): self._update_job(jid, status='cancelled'); return
            self._update_job(jid, status='running')
            def progress(value, message=''):
                if isinstance(value, dict): message = value.get('message', ''); value = value.get('progress', 0)
                _number(value, 'progress', 0, 1)
                self._update_job(jid, progress=value, message=str(message)[:1000])
            result = processor(session, cancel=event.is_set, progress=progress)
            if event.is_set() or result.get('status') == 'cancelled':
                self._update_job(jid, status='cancelled'); return
            result = dict(result)
            result['job_id'] = jid; result['session_revision'] = session['revision']
            result['recording_manifest'] = [{'capture_id': c['capture_id'], 'sha256': c['sha256'], 'provenance': c['provenance']} for c in session['captures']]
            with self._lock:
                _write_json(self.root / 'jobs' / (jid + '.result.json'), result)
                _write_json(self._session_dir(session['session_id']) / 'result.json', result)
                self._update_job(jid, status='completed', progress=1.)
        except Exception as exc:
            self._update_job(jid, status='cancelled' if event.is_set() else 'failed', error={'code': 'processing_failed', 'message': str(exc)[:1000]})
        finally:
            with self._lock: self._events.pop(jid, None)
    def get_job(self, jid):
        with self._lock:
            p = self._job_path(jid)
            if not p.exists(): raise KeyError('job not found')
            return json.loads(p.read_text())
    def cancel_job(self, jid):
        with self._lock:
            job = self.get_job(jid)
            if jid in self._events:
                self._events[jid].set(); self._update_job(jid, cancellation_requested=True)
            return self.get_job(jid)
    def get_result(self, sid):
        with self._lock:
            s = self._raw_session(sid); p = self._session_dir(sid) / 'result.json'
            if not p.exists(): raise KeyError('result not available')
            result = json.loads(p.read_text()); result['stale'] = result.get('session_revision') != s['revision']
            return result
    def export_session(self, sid, destination=None):
        with self._lock:
            s = self._raw_session(sid); directory = self._session_dir(sid)
            result = directory / 'result.json'
            target = Path(destination) if destination else self.root / 'exports' / (sid + '.zip')
            target.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(prefix='.export-', dir=target.parent); os.close(fd)
            try:
                with zipfile.ZipFile(tmp, 'w', compression=zipfile.ZIP_STORED) as z:
                    z.writestr('session.json', json.dumps(s, allow_nan=False))
                    if result.exists(): z.write(result, 'result.json')
                    for relative in sorted({c['recording_path'] for c in s['captures']}):
                        path = (directory / relative).resolve()
                        if not path.is_relative_to(directory): raise ValueError('recording path escapes session')
                        z.write(path, relative)
                os.replace(tmp, target)
            finally:
                if os.path.exists(tmp): os.unlink(tmp)
            return target
    def import_archive(self, path):
        path = Path(path)
        if path.stat().st_size > MAX_ARCHIVE_BYTES + MAX_JSON_BYTES * 2: raise ValueError('archive exceeds resource limit')
        try:
            with zipfile.ZipFile(path) as z:
                infos = z.infolist(); names = [i.filename for i in infos]
                if len(infos) > MAX_CAPTURES + 2 or len(names) != len(set(names)): raise ValueError('duplicate or too many archive entries')
                if sum(i.file_size for i in infos) > MAX_ARCHIVE_BYTES + MAX_JSON_BYTES * 2: raise ValueError('expanded archive exceeds resource limit')
                if any(i.is_dir() or i.flag_bits & 1 or i.filename.startswith('/') or '..' in Path(i.filename).parts or '\\' in i.filename for i in infos): raise ValueError('unsafe archive member')
                if 'session.json' not in names or z.getinfo('session.json').file_size > MAX_JSON_BYTES: raise ValueError('missing or oversized session.json')
                s = validate_session(json.loads(z.read('session.json')))
                revision = s.get('revision')
                if isinstance(revision, bool) or not isinstance(revision, int) or revision < 0: raise ValueError('archive requires nonnegative integer session revision')
                sid = _id(s.get('session_id')); directory = self._session_dir(sid)
                allowed = {'session.json', 'result.json'} | {c.get('recording_path', '') for c in s['captures']}
                if set(names) - allowed: raise ValueError('unexpected archive member')
                with self._lock:
                    if directory.exists(): raise FileExistsError('session already exists')
                    stage = Path(tempfile.mkdtemp(prefix='.import-', dir=self.root / 'sessions'))
                    try:
                        for cap in s['captures']:
                            relative = cap.get('recording_path', '')
                            if not re.fullmatch(r'raw/[a-f0-9]{64}\.(wav|csv|zip)', relative): raise ValueError('invalid raw recording path')
                            if z.getinfo(relative).file_size > MAX_RECORDING_BYTES: raise ValueError('recording exceeds resource limit')
                            raw = z.read(relative)
                            if hashlib.sha256(raw).hexdigest() != cap.get('sha256'): raise ValueError('recording checksum mismatch')
                            if relative.split('/')[-1].split('.')[0] != cap.get('sha256'): raise ValueError('raw filename does not match content hash')
                            _atomic_bytes(stage / relative, raw)
                            actual = import_recording(stage / relative, stage / 'raw')
                            if Path(actual['recording_path']).relative_to(stage).as_posix() != relative: raise ValueError('raw extension does not match recording format')
                            cap.update(actual); cap['recording_path'] = relative
                        s['replay'] = {'kind': 'archive_reload', 'archive_sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'loaded_at': time.time()}
                        _write_json(stage / 'session.json', s)
                        if 'result.json' in names:
                            if z.getinfo('result.json').file_size > MAX_JSON_BYTES: raise ValueError('result metadata too large')
                            result = json.loads(z.read('result.json')); _write_json(stage / 'result.json', result)
                        os.replace(stage, directory)
                    finally:
                        if stage.exists(): shutil.rmtree(stage)
                return self.get_session(sid)
        except (zipfile.BadZipFile, KeyError, UnicodeError) as exc:
            raise ValueError('invalid archive') from exc
