"""LOMINII Auth Room – Signup, Login, Guest, Google, Phone OTP (Real DB)"""
from datetime import datetime, timedelta
import os
from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from lominii_platform.lomimail import (
    normalize_phone_uid,
    generate_lomimail_address,
    calculate_lomimail_placement,
)
from lominii_platform.auth import verify_password, get_password_hash, get_current_user
from lominii_platform.bubblejumbo import (
    create_token as create_bjt,
    record_failure,
    reset_failures,
    get_required_copies,
    get_failure_count
)
from lominii_platform.content_filter import is_blocked
from lominii_platform.database import get_db
from lominii_platform.models.public import User, OTP
from lominii_platform.otp_service import generate_otp, send_otp
import re

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
    creator_role = data.get("creator_role", "creator").strip().lower()
    news_category = data.get("news_category", "").strip()

    # Validation
    if not is_valid_email(email):
        raise HTTPException(status_code=400, detail="Invalid email format")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    if not full_name:
        raise HTTPException(status_code=400, detail="Full name is required")
    if creator_role not in ("creator", "newscaster"):
        raise HTTPException(status_code=400, detail="Invalid creator role")
    if creator_role == "newscaster" and not news_category:
        raise HTTPException(status_code=400, detail="News category required for newscasters")
    if is_blocked(email) or is_blocked(password) or is_blocked(full_name):
        raise HTTPException(status_code=400, detail="Blocked content")

    # Check existing user
    existing = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="User already exists")

    # Create user
    account_preferences = {"creator_role": creator_role}
    if creator_role == "newscaster":
        account_preferences["news_category"] = news_category

    user = User(
        email=email,
        full_name=full_name,
        password_hash=get_password_hash(password),
        news_preferences=account_preferences,
    )
    db.add(user)
    await db.commit()

    # Issue token (normal K=5, no failures yet)
    token = create_bjt(email)
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
    if not user or not user.password_hash or not verify_password(password, user.password_hash):
        fails = await record_failure(email, db)
        raise HTTPException(
            status_code=401,
            detail=(
                "Invalid credentials. Warning: account security "
                f"increased after 5 failures. (Attempt {fails})"
            ),
        )

    # Preserve the current security level for this token, then reset failures.
    copies = await get_required_copies(email, db)
    await reset_failures(email, db)

    # Use email as the token identity for protected account endpoints.
    token = create_bjt(email, copies=copies)
    return {"access_token": token, "token_type": "bearer", "email": email}

# ---------------------------------------------------------------------------
# Guest Session
# ---------------------------------------------------------------------------
@router.post("/guest")
async def guest():
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

    user = (await db.execute(select(User).where((User.google_id == google_id) | (User.email == email)))).scalar_one_or_none()
    if not user:
        user = User(
            email=email,
            full_name=full_name,
            google_id=google_id,
            password_hash=""
        )
        db.add(user)
        await db.commit()
    else:
        if not user.google_id:
            user.google_id = google_id
            await db.commit()

    token = create_bjt(user.email)
    return {"access_token": token, "token_type": "bearer", "email": user.email}

# ---------------------------------------------------------------------------
# Phone OTP – Request
# ---------------------------------------------------------------------------

def _validate_registration_phone(data):
    """Validate an international phone number against the selected country."""
    try:
        import phonenumbers
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="Phone validation dependency missing; install phonenumbers.",
        )

    raw_phone = data.get("phone", "")
    region = data.get("country_iso2", "")
    country = data.get("country", "")

    if not isinstance(region, str) or len(region.strip()) != 2:
        raise HTTPException(
            status_code=400,
            detail="Select a country and send its two-letter country_iso2 code.",
        )

    region = region.strip().upper()
    if region not in phonenumbers.SUPPORTED_REGIONS:
        raise HTTPException(status_code=400, detail="Unsupported country code.")

    if not isinstance(country, str) or not country.strip():
        raise HTTPException(status_code=400, detail="Country is required.")

    try:
        import pycountry
        selected_country = pycountry.countries.lookup(country.strip())
    except (LookupError, ImportError):
        raise HTTPException(status_code=400, detail="Country not recognized.")

    if selected_country.alpha_2 != region:
        raise HTTPException(
            status_code=400,
            detail="Selected country and country_iso2 do not match.",
        )

    country = selected_country.name

    try:
        phone = normalize_phone_uid(raw_phone)
        parsed = phonenumbers.parse(phone, region)
    except (ValueError, phonenumbers.NumberParseException) as exc:
        raise HTTPException(status_code=400, detail="Invalid phone number.") from exc

    if not phonenumbers.is_valid_number(parsed):
        raise HTTPException(status_code=400, detail="Invalid phone number.")

    if not phonenumbers.is_valid_number_for_region(parsed, region):
        raise HTTPException(
            status_code=400,
            detail="Phone number does not match the selected country.",
        )

    return phone, region, country.strip()


def _profile_text(data, key, limit=150, required=False):
    value = data.get(key, "")
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise HTTPException(status_code=400, detail=f"{key} must be text.")
    value = value.strip()
    if len(value) > limit:
        raise HTTPException(
            status_code=400,
            detail=f"{key} must not exceed {limit} characters.",
        )
    if required and not value:
        raise HTTPException(status_code=400, detail=f"{key} is required.")
    return value or None


@router.post("/phone/request")
async def phone_request(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        data = await request.json()
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(status_code=400, detail="Invalid JSON request body")

    if not isinstance(data, dict):
        raise HTTPException(status_code=400, detail="Request body must be a JSON object")

    phone, region, country = _validate_registration_phone(data)

    otp_code = generate_otp()
    otp_record = OTP(
        phone=phone,
        code=otp_code,
        expires_at=datetime.utcnow() + timedelta(minutes=5),
        verified=False,
    )
    db.add(otp_record)

    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Could not create OTP request.")

    try:
        sent = await send_otp(phone, otp_code)
    except Exception:
        sent = False

    # Development OTP is returned only when explicitly enabled on the
    # designated beta hostname. Normal production requests never expose it.
    dev_otp_enabled = (
        os.getenv("DEV_OTP_ENABLED", "").strip().lower() == "true"
        and request.url.hostname == "lominii-search-beta.onrender.com"
    )

    if not sent and not dev_otp_enabled:
        raise HTTPException(
            status_code=502,
            detail="OTP delivery failed. Request a new code."
        )

    result = {
        "message": (
            "Development OTP ready for testing"
            if dev_otp_enabled
            else "OTP sent successfully"
        ),
        "phone": phone,
        "country": country,
        "country_iso2": region,
        "expires_in_seconds": 300,
    }

    if dev_otp_enabled:
        result["dev_otp"] = otp_code
        result["development_mode"] = True

    return result


@router.post("/phone/verify")
async def phone_verify(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        data = await request.json()
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(status_code=400, detail="Invalid JSON request body")

    if not isinstance(data, dict):
        raise HTTPException(status_code=400, detail="Request body must be a JSON object")

    phone, region, country = _validate_registration_phone(data)
    otp_input = data.get("otp", "")

    if not isinstance(otp_input, str) or not otp_input.strip():
        raise HTTPException(status_code=400, detail="OTP is required")
    otp_input = otp_input.strip()

    otp_record = (
        await db.execute(
            select(OTP)
            .where(OTP.phone == phone, OTP.verified.is_(False))
            .order_by(OTP.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    if not otp_record:
        raise HTTPException(status_code=400, detail="No OTP requested for this number")
    if datetime.utcnow() > otp_record.expires_at:
        raise HTTPException(status_code=400, detail="OTP expired. Request a new code.")
    if otp_record.code != otp_input:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    users = (
        await db.execute(
            select(User).where((User.lomimail_uid == phone) | (User.phone == phone))
        )
    ).scalars().all()

    if len(users) > 1:
        raise HTTPException(
            status_code=409,
            detail="This phone matches multiple accounts; reconciliation is required.",
        )

    user = users[0] if users else None

    if user is None:
        full_name = data.get("full_name")
        password = data.get("password")

        if not isinstance(full_name, str) or not full_name.strip():
            raise HTTPException(status_code=400, detail="Full name is required.")
        full_name = full_name.strip()

        if not isinstance(password, str) or len(password) < 6:
            raise HTTPException(
                status_code=400,
                detail="Password is required and must be at least 6 characters.",
            )

        state = _profile_text(data, "state", 100, required=True)
        lga = _profile_text(data, "lga", 100, required=True)
        city = _profile_text(data, "city", 100, required=True)
        community1 = _profile_text(
            data, "primary_community_1", 150, required=True
        )
        community2 = _profile_text(data, "primary_community_2", 150)
        picture = _profile_text(data, "profile_picture_url", 500)
        additional_image = _profile_text(data, "additional_image_url", 500)

        user = User(
            email=f"{phone}@lominii.local",
            full_name=full_name,
            password_hash=get_password_hash(password),
            phone=phone,
            country=country,
            state=state,
            lga=lga,
            city=city,
            primary_community_1=community1,
            primary_community_2=community2,
            profile_picture_url=picture,
            additional_image_url=additional_image,
        )
        db.add(user)
        await db.flush()
    else:
        # Existing accounts keep their established name, password and profile.
        user.phone = phone

    if not user.lomimail_address:
        result = await db.execute(
            select(User.lomimail_address).where(
                User.lomimail_address.is_not(None)
            )
        )
        existing_addresses = [row[0] for row in result.all() if row[0]]
        try:
            user.lomimail_address = generate_lomimail_address(
                user.full_name, existing_addresses
            )
        except ValueError as exc:
            await db.rollback()
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    placement = calculate_lomimail_placement(user.full_name, phone)
    user.lomimail_uid = phone
    user.phone_verified = True
    user.lomimail_handshake_at = datetime.utcnow()
    user.lomimail_startrow = placement["start_row"]
    otp_record.verified = True

    try:
        await db.commit()
        await db.refresh(user)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Identity conflict occurred. Please retry verification.",
        )

    token = create_bjt(user.email)
    return {
        "access_token": token,
        "token_type": "bearer",
        "phone": phone,
        "country": getattr(user, "country", None) or country,
        "lomimail_address": user.lomimail_address,
        "uID": user.lomimail_uid,
        "full_name": user.full_name,
        "start_row": user.lomimail_startrow,
        "profile": {
            "state": getattr(user, "state", None),
            "lga": getattr(user, "lga", None),
            "city": getattr(user, "city", None),
            "primary_community_1": getattr(user, "primary_community_1", None),
            "primary_community_2": getattr(user, "primary_community_2", None),
            "profile_picture_url": getattr(user, "profile_picture_url", None),
            "additional_image_url": getattr(user, "additional_image_url", None),
        },
    }


@router.get("/failure-count")
async def failure_count(email: str = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    count = await get_failure_count(email, db)
    return {"failures": count}

@router.post("/reset-failures")
async def reset_failures_endpoint(email: str = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await reset_failures(email, db)
    return {"message": "Failure counter reset"}

# ---------------------------------------------------------------------------
# Preference setting.
# ---------------------------------------------------------------------------

@router.put("/preferences")
async def save_preferences(request: Request, db: AsyncSession = Depends(get_db), email: str = Depends(get_current_user)):
    data = await request.json()
    user = (await db.execute(select(User).where(User.email == email))).scalar_one()
    # data_sources is part of news_preferences – we merge them
    current = user.news_preferences or {}
    current["wikipedia"] = data.get("wikipedia", False)
    current["banking"] = data.get("banking", False)
    current["news"] = data.get("news", True)
    current["dictionary"] = data.get("dictionary", True)
    user.news_preferences = current
    # also update language & country if provided
    if "language" in data:
        user.language = data["language"]
    if "country" in data:
        # You may want to add a country column, but for now we can store in news_preferences
        current["country"] = data["country"]
        user.news_preferences = current
    await db.commit()
    return {"message": "Preferences saved"}


@router.get("/preferences")
async def get_preferences(email: str = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    user = (await db.execute(select(User).where(User.email == email))).scalar_one()
    prefs = user.news_preferences or {}
    return {
        "language": user.language,
        "country": prefs.get("country", "Nigeria"),
        "data_sources": {
            "wikipedia": prefs.get("wikipedia", False),
            "banking": prefs.get("banking", False),
            "news": prefs.get("news", True),
            "dictionary": prefs.get("dictionary", True),
        }
    }