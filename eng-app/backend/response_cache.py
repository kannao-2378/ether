"""Process-local TTL cache for expensive read-only API responses.

Single uvicorn worker keeps this safe. Keys must include the database identity
so test mode and real mode never share entries. Write endpoints invalidate only
the domains they actually change via bump(...); entries also expire by TTL.

HTTP read routes may opt into stale-while-revalidate: a bumped/expired entry is
served immediately while a background worker recomputes it, so pages such as
the study plan or profile stay instant right after each answer. Scheduler code
must NOT opt in - it always needs synchronous, exact values.
"""
import os
import queue
import threading
import time
from contextvars import ContextVar

_lock=threading.Lock()
_store={}
_versions={}
_MAX_ENTRIES=256
_MAX_STALE=600.0
_http_scope=ContextVar('response_cache_http',default=False)

_refresh_queue=queue.Queue()
_pending=set()
_worker_started=False

def begin_http():
    """Mark the current task as an HTTP request allowed to serve stale values.

    Test runs keep synchronous semantics so write-then-read assertions hold.
    """
    if 'PYTEST_CURRENT_TEST' in os.environ:return None
    return _http_scope.set(True)

def end_http(token):
    if token is not None:_http_scope.reset(token)

def http_active():
    """True inside a real (non-test) HTTP request. Function calls and tests are False."""
    return _http_scope.get()

def bump(*domains,hard=False):
    """Advance the invalidation version of the given domains; no domains = reset all.

    Entries are kept (not deleted): reads that opt into stale-while-revalidate
    can still serve the previous value while a refresh runs. Pass hard=True for
    rare structural writes (settings, imports) where serving the previous value
    even once would mislead the user.
    """
    with _lock:
        if not domains:
            _versions.clear();_store.clear();return
        for d in domains:_versions[d]=_versions.get(d,0)+1
        if hard:
            for key in [k for k in _store if k[0] in domains]:del _store[key]

def _worker():
    while True:
        domain,key,ttl,compute=_refresh_queue.get()
        try:
            with _lock:version=_versions.get(domain,0)
            try:value=compute()
            except Exception:continue
            with _lock:
                if len(_store)>=_MAX_ENTRIES:_store.clear()
                _store[(domain,key)]=(time.monotonic()+ttl,value,version)
        finally:
            with _lock:_pending.discard((domain,key))
            _refresh_queue.task_done()

def _ensure_worker():
    global _worker_started
    if not _worker_started:
        _worker_started=True
        threading.Thread(target=_worker,daemon=True,name='response-cache-refresh').start()

def cached(domain,key,ttl,compute,swr=False):
    """Return the cached value for (domain,key), or compute() and cache it for ttl seconds.

    With swr=True inside an HTTP request, a stale entry (version bumped or TTL
    expired within the staleness window) is returned immediately and refreshed
    on a background thread.
    """
    now=time.monotonic()
    with _lock:
        version=_versions.get(domain,0)
        hit=_store.get((domain,key))
        if hit and hit[0]>now and hit[2]==version:
            return hit[1]
        serve_stale=swr and _http_scope.get() and hit and now-hit[3]<_MAX_STALE
        if serve_stale:
            _ensure_worker()
            if (domain,key) not in _pending:
                _pending.add((domain,key))
                enqueue=True
            else:
                enqueue=False
        else:
            enqueue=False
    if enqueue:_refresh_queue.put((domain,key,ttl,compute))
    if serve_stale:return hit[1]
    value=compute()
    with _lock:
        if len(_store)>=_MAX_ENTRIES:_store.clear()
        _store[(domain,key)]=(time.monotonic()+ttl,value,version,now)
    return value

def version(domain):
    """Current invalidation counter of a domain, for cheap change detection."""
    with _lock:return _versions.get(domain,0)
