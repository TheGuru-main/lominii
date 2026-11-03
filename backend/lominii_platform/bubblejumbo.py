"""BubbleJumbo Token Service (Platform Layer)
JWT‑like tokens with embedded GSP cell + dynamic K‑escalation on attack.
Now persists failure counters in PostgreSQL.
"""
import os
import time
from jose import jwt, JWTError
from lominii_platform.gsp import gsp_place, query_marker
from sqlalchemy import select
from lominii_platform.models.public import BubbleJumboFailure, User


SECRET_KEY = os.getenv("JWT_SECRET", "").strip()
if not SECRET_KEY:
    raise RuntimeError(
        "JWT_SECRET must be configured in the environment before startup"
    )
ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "10080"))

# ── Database helper (import lazily to avoid circular import at module level) ──

async def _get_failure_row(identity: str, db):
    row = (await db.execute(select(BubbleJumboFailure).where(BubbleJumboFailure.identity == identity))).scalar_one_or_none()
    return row

async def _save_failure_row(identity: str, failures: int, db):
    from lominii_platform.models.public import BubbleJumboFailure
    row = await _get_failure_row(identity, db)
    if row:
        row.failures = failures
    else:
        row = BubbleJumboFailure(identity=identity, failures=failures)
        db.add(row)
    await db.commit()

# ── Public API (used by auth router) ──

async def record_failure(identity: str, db) -> int:
    """Increment the failed‑login counter for this identity, return new count."""
    row = await _get_failure_row(identity, db)
    current = row.failures if row else 0
    new_count = current + 1
    await _save_failure_row(identity, new_count, db)
    return new_count

async def reset_failures(identity: str, db):
    """Clear the counter after a successful login."""
    await _save_failure_row(identity, 0, db)

async def get_failure_count(identity: str, db) -> int:
    """Return current failure count (used by the GET endpoint)."""
    row = await _get_failure_row(identity, db)
    return row.failures if row else 0

async def get_required_copies(identity: str, db) -> int:
    """
    Return the number of replicas (K) for the security token.
    Below 5 failures → normal K=5.
    For every failure beyond 5, we add 1 extra replica (capped at 20).
    """
    fails = await get_failure_count(identity, db)
    if fails <= 5:
        return 5
    return min(5 + (fails - 5), 20)

# ── Token creation & verification (unchanged, except now need db for copies) ──

# Identity strings (email, phone, guest id) always use the English face so a
# user's token does not change when the interface language changes.
IDENTITY_LANGUAGE = "en"
# Tokens issued before alphabet-length columns carry no "C" and used 56.
LEGACY_COLUMNS = 56
MAX_COPIES = 20


def _copies(value) -> int:
    try:
        value = int(value)
    except (TypeError, ValueError):
        return 5
    return max(1, min(value, MAX_COPIES))


def create_token(identity: str, copies: int = None, C: int = None, R: int = 64) -> str:
    marker = query_marker(identity, IDENTITY_LANGUAGE)
    columns = C or marker["columns"]
    K = _copies(copies)   # default 5; caller passes get_required_copies()
    cells = gsp_place(marker["L"], marker["S"], marker["c"], K=K, C=columns, R=R)
    primary = cells["primary_cell"]
    now = int(time.time())
    payload = {
        "sub": identity,
        "iat": now,
        "exp": now + TOKEN_EXPIRE_MINUTES * 60,
        "bj": {
            "col": primary["col"],
            "row": primary["row"],
            "L": marker["L"],
            "S": marker["S"],
            "c": marker["c"],
            "K": K,
            "C": columns,
            "face": marker["face"],
            "lang": IDENTITY_LANGUAGE,
        }
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str, C: int = None, R: int = 64) -> dict | None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None
    bj = payload.get("bj", {})
    L, S, c = bj.get("L"), bj.get("S"), bj.get("c")
    if L is None or S is None or c is None:
        return None
    columns = C or bj.get("C") or LEGACY_COLUMNS
    if not isinstance(columns, int) or not 1 <= columns <= 64:
        return None
    cells = gsp_place(L, S, c, K=_copies(bj.get("K")), C=columns, R=R)
    primary = cells["primary_cell"]
    if primary["col"] != bj.get("col") or primary["row"] != bj.get("row"):
        return None
    return payload
