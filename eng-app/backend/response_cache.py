"""Process-local TTL cache for expensive read-only API responses.

Single uvicorn worker keeps this safe. Keys must include the database identity
so test mode and real mode never share entries. Write endpoints invalidate only
the domains they actually change via bump(...); entries also expire by TTL.
"""
import time
from threading import Lock

_lock=Lock()
_store={}
_versions={}
_MAX_ENTRIES=256

def bump(*domains):
    """Invalidate cached responses of the given domains; no domains = everything."""
    with _lock:
        if not domains:
            _versions.clear();_store.clear();return
        for d in domains:_versions[d]=_versions.get(d,0)+1
        for key in [k for k in _store if k[0] in domains]:del _store[key]

def cached(domain,key,ttl,compute):
    """Return the cached value for (domain,key), or compute() and cache it for ttl seconds."""
    with _lock:
        version=_versions.get(domain,0)
        hit=_store.get((domain,key))
        if hit and hit[0]>time.monotonic() and hit[2]==version:
            return hit[1]
    value=compute()
    with _lock:
        if len(_store)>=_MAX_ENTRIES:_store.clear()
        _store[(domain,key)]=(time.monotonic()+ttl,version,value)
    return value
