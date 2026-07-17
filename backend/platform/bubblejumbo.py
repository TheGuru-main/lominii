"""BubbleJumbo Token Service (Platform Layer) – Persistent Failure Tracking"""
import os, time, random
from jose import jwt, JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from platform.gsp import calculate_lsum, calculate_ssum, first_letter_index, gsp_place
from platform.models.public import BubbleJumboFailure, User

SECRET_KEY = os.getenv("JWT_SECRET", "changeme")
ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "10080"))

# ---------- Persistent failure helpers (async DB) ----------
async def record_failure(identity: str, db: AsyncSession) -> int:
    """Increment the failed‑login counter for this identity, return new count."""
    row = (await db.execute(
        select(BubbleJumboFailure).where(BubbleJumboFailure.identity == identity)
    )).scalar_one_or_none()
    if row is None:
        row = BubbleJumboFailure(identity=identity, failures=1)
        db.add(row)
    else:
        row.failures += 1
    await db.commit()
    return row.failures

async def reset_failures(identity: str, db: AsyncSession):
    """Clear the counter after a successful login."""
    row = (await db.execute(
        select(BubbleJumboFailure).where(BubbleJumboFailure.identity == identity)
    )).scalar_one_or_none()
    if row:
        await db.delete(row)
        await db.commit()

async def get_failure_count(identity: str, db: AsyncSession) -> int:
    """Return the current failure count."""
    row = (await db.execute(
        select(BubbleJumboFailure).where(BubbleJumboFailure.identity == identity)
    )).scalar_one_or_none()
    return row.failures if row else 0

async def get_required_copies(identity: str, db: AsyncSession) -> int:
    """Return the number of replicas (K) for the security token."""
    fails = await get_failure_count(identity, db)
    if fails <= 5:
        return 5
    return min(5 + (fails - 5), 20)

# ---------- Token creation & verification (unchanged) ----------
def create_token(identity: str, copies: int = None, C: int = 26, R: int = 64) -> str:
    L = calculate_lsum(identity)
    S = calculate_ssum(identity)
    c = first_letter_index(identity)
    if copies is None:
        copies = 5   # caller must pass the correct dynamic K now
    cells = gsp_place(L, S, c, K=copies, C=C, R=R)
    primary = cells["primary_cell"]
    now = int(time.time())
    payload = {
        "sub": identity,
        "iat": now,
        "exp": now + TOKEN_EXPIRE_MINUTES * 60,
        "bj": {
            "col": primary["col"], "row": primary["row"],
            "L": L, "S": S, "c": c, "K": copies
        }
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str, C: int = 26, R: int = 64) -> dict | None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None
    bj = payload.get("bj", {})
    L, S, c, K = bj.get("L"), bj.get("S"), bj.get("c"), bj.get("K")
    if L is None or S is None or c is None:
        return None
    cells = gsp_place(L, S, c, K=K, C=C, R=R)
    primary = cells["primary_cell"]
    if primary["col"] != bj.get("col") or primary["row"] != bj.get("row"):
        return None
    return payload

def challenge(identity: str, copies: int = 5, C: int = 26, R: int = 64) -> dict:
    L = calculate_lsum(identity)
    S = calculate_ssum(identity)
    c = first_letter_index(identity)
    cells = gsp_place(L, S, c, K=copies, C=C, R=R)["cells"]
    chosen = random.choice(cells)
    return {"k": chosen["k"], "cell": chosen, "K": copies}

def verify_challenge(identity: str, k: int, col: int, row: int, copies: int = 5, C: int = 26, R: int = 64) -> bool:
    cells = gsp_place(calculate_lsum(identity), calculate_ssum(identity),
                      first_letter_index(identity), K=copies, C=C, R=R)["cells"]
    if k < len(cells):
        cell = cells[k]
        return cell["col"] == col and cell["row"] == row
    return False