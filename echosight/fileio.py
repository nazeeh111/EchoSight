"""Bounded JSON input and output policies preserving original recordings."""
import json
import math
import os
from pathlib import Path


def require_distinct_output(destination, inputs):
    """Refuse normalized paths and existing symlink/hardlink aliases of inputs."""
    destination = Path(destination)
    resolved = destination.resolve()
    for source in map(Path, inputs):
        aliases = resolved == source.resolve()
        if not aliases:
            try:
                aliases = destination.samefile(source)
            except (FileNotFoundError, NotADirectoryError):
                pass
        if aliases:
            raise ValueError(f'output must be distinct from input: {source}')


def require_new_outputs(paths):
    """Preflight a generated group, including dangling links, before any writes."""
    for path in map(Path, paths):
        if path.exists() or path.is_symlink():
            raise FileExistsError(f'output already exists; choose a fresh destination: {path}')


def require_store_output(destination, root):
    """Exports/results may not replace a store's data, job state or lock file."""
    target, root = Path(destination).resolve(), Path(root).resolve()
    protected = [(root / name).resolve() for name in ('sessions', 'jobs')]
    # Resolve directory ancestry separately: following the final symlink alone
    # can hide that replacing the link itself would alter reserved store data.
    location = Path(os.path.abspath(destination))
    locations = [target, *(parent.resolve() for parent in location.parents)]
    if (target == (root / '.store.lock').resolve() or target == root
            or any(path.is_relative_to(directory) for path in locations for directory in protected)):
        raise ValueError('output must be outside the store sessions, jobs and ownership lock')


def parse_json_object(raw):
    """Decode bounded-structure JSON without ambiguous keys or nonfinite values."""
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate JSON key')
            result[key] = value
        return result
    def invalid_constant(_value):
        raise ValueError('nonfinite JSON constant')
    try:
        value = json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid_constant)
    except (ValueError, UnicodeError, RecursionError) as error:
        raise ValueError('invalid JSON') from error
    if not isinstance(value, dict):
        raise ValueError('JSON must be an object')
    # Keep only container iterators, so a large flat array does not allocate
    # an additional tuple per scalar merely to check depth and finite values.
    stack = [iter(value.values())]
    while stack:
        try:
            item = next(stack[-1])
        except StopIteration:
            stack.pop()
            continue
        if len(stack) > 64:
            raise ValueError('JSON nesting exceeds limit')
        if isinstance(item, float) and not math.isfinite(item):
            raise ValueError('nonfinite JSON number')
        if isinstance(item, dict):
            stack.append(iter(item.values()))
        elif isinstance(item, list):
            stack.append(iter(item))
    return value


def read_bytes_bounded(path, max_bytes):
    """Limit the same byte snapshot that will be decoded, including a growing file."""
    with Path(path).open('rb') as stream:
        raw = stream.read(max_bytes + 1)
    if len(raw) > max_bytes:
        raise ValueError(f'JSON input exceeds byte limit ({max_bytes} bytes)')
    return raw


def read_json_object(path, max_bytes):
    return parse_json_object(read_bytes_bounded(path, max_bytes))
