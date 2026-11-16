"""Caller-owned bounded in-memory DSP observations, never scene results."""
from collections import OrderedDict
import hashlib
import json
from threading import RLock


class ObservationCache:
    """Thread-safe byte-bounded LRU; destroyed when its owner goes away.

    Checksums detect accidental memory corruption, not deliberate forgery.
    Concurrent misses may recompute independently; cancellation never waits on a peer.
    """
    def __init__(self, max_entries=32, max_bytes=16 * 1024 * 1024, max_entry_bytes=1024 * 1024):
        if any(type(x) is not int or x < 1 for x in (max_entries, max_bytes, max_entry_bytes)):
            raise ValueError('cache bounds must be positive integers')
        self.max_entries, self.max_bytes, self.max_entry_bytes = max_entries, max_bytes, max_entry_bytes
        self._entries = OrderedDict()
        self._size = 0
        self._lock = RLock()

    def get(self, key):
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None, 'miss'
            try:
                data, checksum = entry
                if not isinstance(data, bytes) or len(data) > self.max_entry_bytes or hashlib.sha256(key.encode() + data).hexdigest() != checksum:
                    raise ValueError('cache checksum mismatch')
                result = json.loads(data)
                if not isinstance(result, dict) or result.get('status') != 'ok':
                    raise ValueError('invalid cache observation')
            except (ValueError, TypeError, UnicodeError):
                removed = self._entries.pop(key)
                self._size = sum(len(item[0]) for item in self._entries.values()
                                 if isinstance(item, tuple) and len(item) == 2 and isinstance(item[0], bytes))
                return None, 'corrupt'
            self._entries.move_to_end(key)
            return result, 'hit'

    def put(self, key, result):
        try:
            data = json.dumps(result, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
        except (TypeError, ValueError, OverflowError):
            return False
        if len(data) > min(self.max_entry_bytes, self.max_bytes):
            return False
        with self._lock:
            previous = self._entries.pop(key, None)
            if previous is not None:
                self._size -= len(previous[0])
            while self._entries and (len(self._entries) >= self.max_entries or self._size + len(data) > self.max_bytes):
                _, removed = self._entries.popitem(last=False)
                self._size -= len(removed[0])
            self._entries[key] = (data, hashlib.sha256(key.encode() + data).hexdigest())
            self._size += len(data)
        return True

    def clear(self):
        with self._lock:
            self._entries.clear()
            self._size = 0
