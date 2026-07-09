"""BubbleJumbo Token Service (Platform Layer)
JWT‑like tokens with embedded GSP cell – deterministic & stateless.
"""
import os, time
from jose import jwt, JWTError
from .gsp import calculate_lsum, calculate_ssum, first_letter_index, gsp_place

SECRET_KEY = os.getenv("JWT_SECRET", "changeme")
ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "10080"))

# ---------- Token creation & verification ----------
def create_token(identity: str, copies: int = 5, C: int = 26, R: int = 64) -> str:
    """Issue a signed BubbleJumbo Token for the given identity (email or full name)."""
    L = calculate_lsum(identity)
    S = calculate_ssum(identity)
    c = first_letter_index(identity)
    cells = gsp_place(L, S, c, K=copies, C=C, R=R)
    primary = cells["primary_cell"]

    now = int(time.time())
    payload = {
        "sub": identity,
        "iat": now,
        "exp": now + TOKEN_EXPIRE_MINUTES * 60,
        "bj": {
            "col": primary["col"],
            "row": primary["row"],
            "L": L,
            "S": S,
            "c": c
        }
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str, C: int = 26, R: int = 64) -> dict | None:
    """Verify a BubbleJumbo Token. Returns the payload if valid, else None."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None

    # Stateless cell verification: recompute and compare
    bj = payload.get("bj", {})
    L, S, c = bj.get("L"), bj.get("S"), bj.get("c")
    if L is None or S is None or c is None:
        return None

    cells = gsp_place(L, S, c, K=1, C=C, R=R)  # only need the primary
    primary = cells["primary_cell"]
    if primary["col"] != bj.get("col") or primary["row"] != bj.get("row"):
        return None   # cell mismatch – token forged or identity changed

    return payload


# ---------- Zero‑knowledge challenge (unchanged) ----------
def challenge(identity: str, C: int = 26, R: int = 64) -> dict:
    """Return a random cell for the user to answer (proof of ownership)."""
    import random
    L = calculate_lsum(identity)
    S = calculate_ssum(identity)
    c = first_letter_index(identity)
    cells = gsp_place(L, S, c, K=5, C=C, R=R)["cells"]
    chosen = random.choice(cells)
    return {"k": chosen["k"], "cell": chosen}


def verify_challenge(identity: str, k: int, col: int, row: int,
                     C: int = 26, R: int = 64) -> bool:
    """Check if the user correctly answered the challenge."""
    cells = gsp_place(calculate_lsum(identity), calculate_ssum(identity),
                      first_letter_index(identity), K=5, C=C, R=R)["cells"]
    if k < len(cells):
        cell = cells[k]
        return cell["col"] == col and cell["row"] == row
    return False