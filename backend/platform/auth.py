"""Authentication – using BubbleJumbo Tokens (Platform Layer)"""
import os
from datetime import datetime, timedelta
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from .bubblejumbo import create_token, verify_token

SECRET_KEY = os.getenv("JWT_SECRET", "changeme")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "10080"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# ---------- Password helpers ----------
def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

# ---------- Token helpers (delegated to BubbleJumbo) ----------
def issue_token(identity: str) -> str:
    """Create a signed BubbleJumbo Token for a logged‑in user."""
    return create_token(identity)

def validate_token(token: str) -> dict | None:
    """Verify a BubbleJumbo Token and return its payload, or None."""
    return verify_token(token)

# ---------- FastAPI dependency for protected routes ----------
async def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    payload = validate_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload["sub"]