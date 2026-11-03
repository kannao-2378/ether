"""Memoize read-only knowledge/evidence decisions within one /next transaction."""
from contextvars import ContextVar
from contextlib import contextmanager
from functools import wraps
_state=ContextVar('selection_read_cache',default=None)
@contextmanager
def scope():
 token=_state.set({})
 try:yield
 finally:_state.reset(token)
def memoized(fn):
 @wraps(fn)
 def wrapped(c,*args,**kwargs):
  cache=_state.get()
  if cache is None:return fn(c,*args,**kwargs)
  key=(fn.__module__,fn.__name__,id(c),args,tuple(sorted(kwargs.items())))
  if key not in cache:cache[key]=fn(c,*args,**kwargs)
  return cache[key]
 return wrapped
def invalidate():
 cache=_state.get()
 if cache is not None:cache.clear()
