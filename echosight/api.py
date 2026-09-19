"""Local HTTP API. No remote paths, no browser cross-origin access, bounded bodies."""
from __future__ import annotations

import json
import math
import threading
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from .storage import MAX_ARCHIVE_BYTES, MAX_JSON_BYTES, MAX_RECORDING_BYTES, SessionStore


class _Server(ThreadingHTTPServer):
    daemon_threads = True
    request_queue_size = 8
    def __init__(self, *args, **kwargs):
        self._connections = threading.BoundedSemaphore(4)
        super().__init__(*args, **kwargs)
    def process_request(self, request, address):
        if not self._connections.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try: super().process_request(request, address)
        except BaseException:
            self._connections.release()
            raise
    def process_request_thread(self, request, address):
        try: super().process_request_thread(request, address)
        finally: self._connections.release()
    def server_close(self):
        super().server_close()
        if hasattr(self, 'store'): self.store.close()


def create_server(root, host='127.0.0.1', port=8765, processor=None):
    """Bind only loopback. Explicit networking/authentication requires a separate design."""
    if host not in {'127.0.0.1', 'localhost'}: raise ValueError('only loopback binding is supported')
    if processor is None:
        from .pipeline import process_session
        processor = process_session
    store = SessionStore(root)

    class Handler(BaseHTTPRequestHandler):
        server_version = 'EchoSight/1.0'
        def log_message(self, *args): pass
        def setup(self):
            super().setup(); self.connection.settimeout(15)
        def _reply(self, code, data, content_type='application/json'):
            if content_type == 'application/json': data = json.dumps(data, allow_nan=False).encode()
            self.send_response(code); self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store'); self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers(); self.wfile.write(data)
        def _guard(self):
            # Protect a local unauthenticated service against browser DNS rebinding/CSRF.
            authority = self.headers.get('Host', '')
            allowed = {f'127.0.0.1:{self.server.server_address[1]}', f'localhost:{self.server.server_address[1]}'}
            if authority not in allowed: raise PermissionError('Host must identify this loopback service')
            if self.headers.get('Origin') or self.headers.get('Sec-Fetch-Site') == 'cross-site':
                raise PermissionError('browser cross-origin requests are disabled; use the local API client')
            if self.headers.get('Transfer-Encoding'): raise ValueError('transfer encoding unsupported; use Content-Length')
        def _body(self, limit):
            try: count = int(self.headers.get('Content-Length', '0'))
            except ValueError: raise ValueError('invalid Content-Length')
            if count < 0: raise ValueError('Content-Length must be nonnegative')
            if count > limit: raise OverflowError('request body exceeds resource limit')
            raw = self.rfile.read(count)
            if len(raw) != count: raise ValueError('incomplete request body')
            return raw
        def _json_body(self):
            raw = self._body(MAX_JSON_BYTES)
            if not raw: return {}
            try: value = json.loads(raw)
            except (ValueError, UnicodeError): raise ValueError('invalid JSON')
            if not isinstance(value, dict): raise ValueError('JSON body must be an object')
            return value
        def _dispatch(self):
            self._guard()
            route = urlsplit(self.path)
            if route.query or route.fragment: raise ValueError('query strings unsupported')
            p = route.path.strip('/').split('/')
            method = self.command
            if p == ['v1', 'health'] and method == 'GET': return self._reply(200, {'schema_version': '1.0', 'status': 'ok'})
            if p == ['v1', 'compare'] and method == 'POST':
                from .evolution import compare_results
                body = self._json_body()
                for key in ('previous', 'current'):
                    result = body.get(key)
                    if not isinstance(result, dict): raise ValueError('previous/current must be result objects')
                    surfaces = result.get('surfaces', [])
                    if not isinstance(surfaces, list) or len(surfaces) > 64: raise ValueError('comparison supports at most 64 surfaces')
                    for surface in surfaces:
                        if not isinstance(surface, dict): raise ValueError('surface must be an object')
                        normal = surface.get('normal')
                        if not isinstance(normal, list) or len(normal) != 3 or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in normal): raise ValueError('surface normal must contain three finite numbers')
                        if not .999 <= sum(v*v for v in normal) <= 1.001: raise ValueError('surface normal must have unit length')
                        offset = surface.get('offset_m')
                        if isinstance(offset, bool) or not isinstance(offset, (int, float)) or not math.isfinite(offset): raise ValueError('surface offset must be finite')
                        if not isinstance(surface.get('surface_id'), str): raise ValueError('surface_id required')
                return self._reply(200, compare_results(body['previous'], body['current']))
            if p == ['v1', 'sessions'] and method == 'POST': return self._reply(201, store.create_session(self._json_body()))
            if p == ['v1', 'imports'] and method == 'POST':
                raw = self._body(MAX_ARCHIVE_BYTES + MAX_JSON_BYTES * 2)
                with tempfile.TemporaryDirectory(prefix='echosight-import-', dir=store.root) as d:
                    path = Path(d) / 'import.zip'; path.write_bytes(raw)
                    s = store.import_archive(path)
                return self._reply(201, store.public_session(s['session_id']))
            if len(p) >= 3 and p[:2] == ['v1', 'sessions']:
                sid = p[2]
                if len(p) == 3 and method == 'GET': return self._reply(200, store.public_session(sid))
                if len(p) == 4:
                    if p[3] == 'recordings' and method == 'POST':
                        metadata_raw = self.headers.get('X-Capture-Metadata', '{}')
                        if len(metadata_raw) > 8192: raise ValueError('capture metadata exceeds header limit')
                        try: metadata = json.loads(metadata_raw)
                        except ValueError: raise ValueError('invalid X-Capture-Metadata JSON')
                        raw = self._body(MAX_RECORDING_BYTES)
                        with tempfile.TemporaryDirectory(prefix='echosight-upload-', dir=store.root) as d:
                            path = Path(d) / 'recording.wav'; path.write_bytes(raw)
                            capture = store.add_recording(sid, path, metadata)
                        return self._reply(201, capture)
                    if p[3] == 'jobs' and method == 'POST':
                        self._json_body()
                        return self._reply(202, store.start_job(sid, processor))
                    if p[3] == 'result' and method == 'GET': return self._reply(200, store.get_result(sid))
                    if p[3] == 'export' and method == 'GET':
                        path = store.export_session(sid)
                        return self._reply(200, path.read_bytes(), 'application/zip')
            if len(p) >= 3 and p[:2] == ['v1', 'jobs']:
                if len(p) == 3 and method == 'GET': return self._reply(200, store.get_job(p[2]))
                if len(p) == 4 and p[3] == 'cancel' and method == 'POST':
                    self._json_body(); return self._reply(202, store.cancel_job(p[2]))
            raise KeyError('route not found')
        def _handle(self):
            try: self._dispatch()
            except PermissionError as exc: self._reply(403, {'error': {'code': 'forbidden', 'message': str(exc)}})
            except OverflowError as exc: self._reply(413, {'error': {'code': 'resource_limit', 'message': str(exc)}})
            except FileExistsError as exc: self._reply(409, {'error': {'code': 'conflict', 'message': str(exc)}})
            except KeyError as exc: self._reply(404, {'error': {'code': 'not_found', 'message': str(exc)}})
            except (ValueError, TypeError, OSError) as exc: self._reply(400, {'error': {'code': 'invalid_request', 'message': str(exc)}})
            except RuntimeError as exc: self._reply(409, {'error': {'code': 'busy', 'message': str(exc)}})
            except Exception: self._reply(500, {'error': {'code': 'internal_error', 'message': 'Unexpected server error'}})
        do_GET = _handle
        do_POST = _handle

    try: server = _Server((host, port), Handler)
    except BaseException: store.close(); raise
    server.store = store
    return server
