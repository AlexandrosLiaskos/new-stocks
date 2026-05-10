"""
Disk-backed TTL cache.

Keys are namespaced with prefixes (`list:`, `full:`, `hist:`, `quote:`,
`search:`, `exchanges:`); `bust(prefix)` evicts a whole namespace at once.
"""
from __future__ import annotations
from pathlib import Path
from typing import Callable, TypeVar
import diskcache

_CACHE_DIR = Path(__file__).resolve().parent.parent / "_cache"
_CACHE_DIR.mkdir(exist_ok=True)
cache = diskcache.Cache(str(_CACHE_DIR))

# TTLs in seconds
TTL_LIST = 30 * 60          # 30 min — IPO calendar
TTL_FULL = 24 * 60 * 60     # 24 h  — dossier (financials, holders, insider)
TTL_HISTORY_LIVE = 5 * 60   # 5 min — today's chart
TTL_HISTORY_FROZEN = 24 * 60 * 60   # 24 h — older dailies
TTL_QUOTE = 5 * 60
TTL_SEARCH = 10 * 60
TTL_EXCHANGES = 24 * 60 * 60

T = TypeVar("T")


def cached(key: str, ttl: int, fn: Callable[..., T], *args, **kwargs) -> T:
    val = cache.get(key)
    if val is not None:
        return val
    val = fn(*args, **kwargs)
    if val is not None:
        cache.set(key, val, expire=ttl)
    return val


def bust(prefix: str = "") -> int:
    n = 0
    for k in list(cache.iterkeys()):
        if not prefix or str(k).startswith(prefix):
            del cache[k]
            n += 1
    return n
