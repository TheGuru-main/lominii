"""Small in-process sliding-window limiter.

State lives in this worker only, so with several workers the effective limit
is multiplied. It brakes password/OTP guessing and SMS cost; it is not a
replacement for a shared limiter (Redis) if you scale out.
"""
import time
from collections import deque

_hits: dict[str, deque] = {}
_MAX_KEYS = 20000
_LONGEST_WINDOW = 3600  # longest window any caller uses


def check(key: str, limit: int, window: float) -> int:
    """Record one attempt. Returns 0 if allowed, else seconds until a slot frees."""
    if limit <= 0:
        return 0
    now = time.monotonic()
    hits = _hits.setdefault(key, deque())
    while hits and now - hits[0] > window:
        hits.popleft()
    if len(hits) >= limit:
        return max(1, int(window - (now - hits[0])) + 1)
    hits.append(now)
    if len(_hits) > _MAX_KEYS:
        for stale in [k for k, v in _hits.items() if not v or now - v[-1] > _LONGEST_WINDOW]:
            _hits.pop(stale, None)
    return 0


def clear(key: str) -> None:
    _hits.pop(key, None)
