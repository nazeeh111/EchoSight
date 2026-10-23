"""Local HTTP API. No remote paths, no browser cross-origin access, bounded bodies."""
from __future__ import annotations

import json
import secrets
import threading
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from .storage import MAX_EXPORT_BYTES, MAX_COMPARE_BYTES, MAX_JSON_BYTES, MAX_RECORDING_BYTES, SessionStore
from .fileio import parse_json_object as _strict_object



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


def create_server(root, host='127.0.0.1', port=8765, processor=None, *, ui=False):
    """Bind only loopback. Explicit networking/authentication requires a separate design."""
    if host not in {'127.0.0.1', 'localhost'}: raise ValueError('only loopback binding is supported')
    if processor is None:
        from .pipeline import process_session
        processor = process_session
    assets = None
    if ui:
        from .webui import ui_directory
        assets = ui_directory()
    store = SessionStore(root)

    class Handler(BaseHTTPRequestHandler):
        server_version = 'EchoSight/1.0'
        def log_message(self, *args): pass
        def setup(self):
            super().setup(); self.connection.settimeout(15)
        def _reply(self, code, data, content_type='application/json', headers=None):
            if content_type == 'application/json': data = json.dumps(data, allow_nan=False).encode()
            self.send_response(code); self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store'); self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('X-Frame-Options', 'DENY')
            self.send_header('Referrer-Policy', 'no-referrer')
            for name, value in (headers or {}).items(): self.send_header(name, value)
            self.end_headers()
            try: self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError): pass
        def _guard(self, ui_read=False):
            # Default remains native local clients only. --ui opts into a same-origin,
            # process-token browser client; no CORS or remotely chosen proxy target.
            hosts = self.headers.get_all('Host', [])
            allowed = {f'127.0.0.1:{self.server.server_address[1]}', f'localhost:{self.server.server_address[1]}'}
            if len(hosts) != 1 or hosts[0].lower() not in allowed:
                raise PermissionError('Host must identify this loopback service')
            origins = self.headers.get_all('Origin', [])
            sites = self.headers.get_all('Sec-Fetch-Site', [])
            tokens = self.headers.get_all('X-EchoSight-UI-Token', [])
            if (len(origins) > 1 or len(sites) > 1 or len(tokens) > 1
                    or (origins and origins[0] != 'http://' + hosts[0].lower())
                    or (sites and sites[0] not in {'same-origin', 'none'})):
                raise PermissionError('cross-origin browser requests are disabled')
            if ui_read:
                if not self.server.ui_assets or self.command != 'GET':
                    raise PermissionError('UI is not enabled')
            elif origins or sites or tokens:
                if (not self.server.ui_assets or len(tokens) != 1 or
                        not secrets.compare_digest(tokens[0].encode(), self.server.ui_token.encode())):
                    raise PermissionError('browser API access requires this process UI token; start with --ui')
            if self.headers.get_all('Transfer-Encoding'):
                raise ValueError('transfer encoding unsupported; use Content-Length')
        def _body(self, limit):
            lengths = self.headers.get_all('Content-Length', [])
            if not lengths: count = 0
            elif (len(lengths) != 1 or len(lengths[0]) > 10
                    or not lengths[0].isascii() or not lengths[0].isdigit()):
                raise ValueError('invalid Content-Length')
            else: count = int(lengths[0])
            if count > limit: raise OverflowError('request body exceeds resource limit')
            raw = self.rfile.read(count)
            if len(raw) != count: raise ValueError('incomplete request body')
            return raw
        def _json_body(self, limit=MAX_JSON_BYTES):
            raw = self._body(limit)
            if not raw: return {}
            return _strict_object(raw)
        def _dispatch(self):
            route = urlsplit(self.path)
            ui_read = bool(self.server.ui_assets) and (route.path.startswith('/ui/') or route.path == '/') and self.command == 'GET'
            self._guard(ui_read=ui_read)
            if route.scheme or route.netloc or route.query or route.fragment:
                raise ValueError('absolute URLs, query strings and fragments unsupported')
            if ui_read:
                if route.path == '/': return self._reply(303, {}, headers={'Location': '/ui/results.html'})
                if route.path == '/ui/config':
                    return self._reply(200, {'schema_version': '1.0', 'enabled': True,
                        'token': self.server.ui_token, 'limits': {'recording_bytes': MAX_RECORDING_BYTES,
                        'archive_bytes': MAX_EXPORT_BYTES, 'json_bytes': MAX_JSON_BYTES}})
                from .webui import read_asset
                data, content_type, headers = read_asset(self.server.ui_assets, route.path)
                return self._reply(200, data, content_type, headers)

            p = route.path.strip('/').split('/')
            method = self.command
            if p == ['v1', 'health'] and method == 'GET': return self._reply(200, {'schema_version': '1.0', 'status': 'ok'})
            if p == ['v1', 'compare'] and method == 'POST':
                from .evolution import compare_results
                body = self._json_body(MAX_COMPARE_BYTES)
                for key in ('previous', 'current'):
                    result = body.get(key)
                    if not isinstance(result, dict): raise ValueError('previous/current must be result objects')
                    surfaces = result.get('surfaces', [])
                    if not isinstance(surfaces, list) or len(surfaces) > 64: raise ValueError('comparison supports at most 64 surfaces')
                return self._reply(200, compare_results(body['previous'], body['current'], previous_comparison=body.get('previous_comparison')))
            if p == ['v1', 'controlled-jobs'] and method == 'POST':
                return self._reply(202,store.start_controlled_job(self._json_body()))
            if p == ['v1', 'sessions'] and method == 'POST': return self._reply(201, store.create_session(self._json_body()))
            if p == ['v1', 'imports'] and method == 'POST':
                raw = self._body(MAX_EXPORT_BYTES)
                with tempfile.TemporaryDirectory(prefix='echosight-import-', dir=store.root) as d:
                    path = Path(d) / 'import.zip'; path.write_bytes(raw)
                    s = store.import_archive(path)
                return self._reply(201, store.public_session(s['session_id']))
            if len(p) >= 3 and p[:2] == ['v1', 'sessions']:
                sid = p[2]
                if len(p) == 3 and method == 'GET': return self._reply(200, store.public_session(sid))
                if len(p) == 3 and method == 'PATCH': return self._reply(200, store.update_calibration(sid, self._json_body()))
                if len(p) == 4:
                    if p[3] == 'recordings' and method == 'POST':
                        metadata_headers = self.headers.get_all('X-Capture-Metadata', [])
                        if len(metadata_headers) > 1: raise ValueError('duplicate capture metadata header')
                        metadata_raw = metadata_headers[0] if metadata_headers else '{}'
                        if len(metadata_raw) > 8192: raise ValueError('capture metadata exceeds header limit')
                        metadata = _strict_object(metadata_raw)
                        raw = self._body(MAX_RECORDING_BYTES)
                        with tempfile.TemporaryDirectory(prefix='echosight-upload-', dir=store.root) as d:
                            path = Path(d) / 'recording.wav'; path.write_bytes(raw)
                            checksums = self.headers.get_all('X-Recording-SHA256', [])
                            if len(checksums) > 1: raise ValueError('duplicate recording checksum header')
                            capture = store.add_recording(sid, path, metadata,
                                expected_sha256=checksums[0] if checksums else None)
                        return self._reply(201, capture)
                    if p[3] == 'jobs' and method == 'POST':
                        body = self._json_body()
                        if set(body) - {'request_id'} or ('request_id' in body and not isinstance(body['request_id'], str)):
                            raise ValueError('job start accepts only an optional request_id string')
                        return self._reply(202, store.start_job(sid, processor, request_id=body.get('request_id')))
                    if p[3] == 'result' and method == 'GET': return self._reply(200, store.get_result(sid))
                    if p[3] == 'material-reference' and method == 'POST':
                        return self._reply(200, store.material_reference(sid, self._json_body()))
                    if p[3] == 'export' and method == 'GET':
                        path = store.export_session(sid)
                        return self._reply(200, path.read_bytes(), 'application/zip')
            if len(p) >= 3 and p[:2] == ['v1', 'jobs']:
                if len(p) == 3 and method == 'GET': return self._reply(200, store.get_job(p[2]))
                if len(p) == 4 and p[3] == 'result' and method == 'GET':
                    return self._reply(200,store.get_job_result(p[2]))
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
        do_PATCH = _handle

    try: server = _Server((host, port), Handler)
    except BaseException: store.close(); raise
    server.store = store
    server.ui_assets = assets
    server.ui_token = secrets.token_urlsafe(32) if assets else ''
    return server
