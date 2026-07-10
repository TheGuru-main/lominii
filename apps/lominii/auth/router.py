"""LOMINII Auth Room – Signup, Login, Guest, Google, Phone OTP (Real DB)"""
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from platform.auth import verify_password, get_password_hash, create_access_token
from platform.bubblejumbo import (
    create_token as create_bjt,
    record_failure,
    reset_failures,
    get_required_copies
)
from platform.content_filter import is_blocked
from platform.database import get_db
from platform.models import User
import re
from platform.otp_service import generate_otp, send_otp
from platform.models import OTP
from sqlalchemy import delete as sql_delete

router = APIRouter(prefix="/auth", tags=["Auth"])

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def is_valid_email(email: str) -> bool:
    return re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", email) is not None

# ---------------------------------------------------------------------------
# Email + Password Signup
# ---------------------------------------------------------------------------
@router.post("/signup")
async def signup(request: Request, db: AsyncSession = Depends(get_db)):
    data = await request.json()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    full_name = data.get("full_name", "").strip()

    # Validation
    if not is_valid_email(email):
        raise HTTPException(status_code=400, detail="Invalid email format")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    if not full_name:
        raise HTTPException(status_code=400, detail="Full name is required")
    if is_blocked(email) or is_blocked(password) or is_blocked(full_name):
        raise HTTPException(status_code=400, detail="Blocked content")

    # Check existing user
    existing = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="User already exists")

    # Create user
    user = User(
        email=email,
        full_name=full_name,
        password_hash=get_password_hash(password)
    )
    db.add(user)
    await db.commit()

    # Issue token (normal K=5, no failures yet)
    token = create_bjt(full_name)
    return {"access_token": token, "token_type": "bearer", "email": email}

# ---------------------------------------------------------------------------
# Email + Password Login (with dynamic K‑escalation)
# ---------------------------------------------------------------------------
@router.post("/login")
async def login(request: Request, db: AsyncSession = Depends(get_db)):
    data = await request.json()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password required")

    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()

    # Check credentials
    if not user or not verify_password(password, user.password_hash):
        fails = record_failure(email)
        raise HTTPException(
            status_code=401,
            detail=f"Invalid credentials. Warning: account security increased after 5 failures. (Attempt {fails})"
        )

    # Successful login – reset failure counter and issue token with dynamic K
    reset_failures(email)
    copies = get_required_copies(email)   # normally 5, higher after an attack
    token = create_bjt(user.full_name, copies=copies)

    return {"access_token": token, "token_type": "bearer", "email": email}

# ---------------------------------------------------------------------------
# Guest Session
# ---------------------------------------------------------------------------
@router.post("/guest")
async def guest():
    # Generate a temporary, anonymous token
    import uuid
    guest_name = f"guest-{uuid.uuid4().hex[:8]}"
    token = create_bjt(guest_name)
    return {"access_token": token, "token_type": "bearer", "guest": True}

# ---------------------------------------------------------------------------
# Google OAuth (placeholder – real verification can be added later)
# ---------------------------------------------------------------------------
@router.post("/google")
async def google_auth(request: Request, db: AsyncSession = Depends(get_db)):
    data = await request.json()
    google_id = data.get("google_id")
    email = data.get("email", "").strip().lower()
    full_name = data.get("full_name", "").strip()

    if not google_id or not email or not full_name:
        raise HTTPException(status_code=400, detail="Missing Google credentials")

    # Check if user exists by Google ID or email
    user = (await db.execute(select(User).where((User.google_id == google_id) | (User.email == email)))).scalar_one_or_none()
    if not user:
        # Create new user
        user = User(
            email=email,
            full_name=full_name,
            google_id=google_id,
            password_hash=""   # no password for Google users
        )
        db.add(user)
        await db.commit()
    else:
        # Update Google ID if needed
        if not user.google_id:
            user.google_id = google_id
            await db.commit()

    token = create_bjt(user.full_name)
    return {"access_token": token, "token_type": "bearer", "email": user.email}

# ---------------------------------------------------------------------------
# Phone OTP – Request
# ---------------------------------------------------------------------------
@router.post("/phone/request")
async def phone_request(request: Request, db: AsyncSession = Depends(get_db)):
    data = await request.json()
    phone = data.get("phone", "").strip()
    if not phone:
        raise HTTPException(status_code=400, detail="Phone number required")

    # 1. Generate OTP and expiry (5 minutes)
    otp_code = generate_otp()
    expires = datetime.utcnow() + timedelta(minutes=5)

    # 2. Save OTP in database
    otp_entry = OTP(phone=phone, code=otp_code, expires_at=expires)
    db.add(otp_entry)
    await db.commit()

    # 3. Send via Africa's Talking
    success = await send_otp(phone, otp_code)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to send OTP. Please try again.")

    return {"message": "OTP sent successfully"}


# ---------------------------------------------------------------------------
# Phone OTP – Verify
# ---------------------------------------------------------------------------
@router.post("/phone/verify")
async def phone_verify(request: Request, db: AsyncSession = Depends(get_db)):
    data = await request.json()
    phone = data.get("phone", "").strip()
    otp_input = data.get("otp", "").strip()
    full_name = data.get("full_name", "").strip()

    if not phone or not otp_input or not full_name:
        raise HTTPException(status_code=400, detail="Missing fields")

    # 1. Find the most recent unused OTP for this phone
    otp_record = (await db.execute(
        select(OTP).where(OTP.phone == phone, OTP.verified == False)
        .order_by(OTP.created_at.desc()).limit(1)
    )).scalar_one_or_none()

    if not otp_record:
        raise HTTPException(status_code=400, detail="No OTP requested for this number")

    # 2. Check expiry
    if datetime.utcnow() > otp_record.expires_at:
        raise HTTPException(status_code=400, detail="OTP expired. Please request a new one.")

    # 3. Verify code
    if otp_record.code != otp_input:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    # 4. Mark OTP as used
    otp_record.verified = True
    await db.commit()

    # 5. Find or create user by phone
    user = (await db.execute(select(User).where(User.phone == phone))).scalar_one_or_none()
    if not user:
        user = User(
            email=f"{phone}@lominii.local",
            full_name=full_name,
            phone=phone,
            password_hash=""
        )
        db.add(user)
        await db.commit()

    token = create_bjt(full_name)
    return {"access_token": token, "token_type": "bearer", "phone": phone}