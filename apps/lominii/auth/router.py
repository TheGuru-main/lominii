"""LOMINII Auth Room – Signup, Login, Guest, Google, Phone OTP (Real DB)"""
from datetime import datetime, timedelta
import hmac
import os
import logging
import time
from urllib.parse import urlparse
import httpx
from jose import jwt as jose_jwt, JWTError
from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from lominii_platform.lomimail import (
    LOMIMAIL_DOMAIN,
    normalize_lomimail_local_part,
    normalize_phone_uid,
    generate_lomimail_address,
    calculate_lomimail_placement,
)
from lominii_platform.auth import verify_password, get_password_hash, get_current_user, validate_token
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
from lominii_platform import ratelimit
from lominii_platform.keymaps.keyboard import SUPPORTED_LANGUAGES
import re

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Auth"])

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def is_valid_email(email: str) -> bool:
    return re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", email) is not None

# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Shared helpers: request parsing, throttling, phone numbers, account payload
# ---------------------------------------------------------------------------
PLACEHOLDER_EMAIL_SUFFIX = "@lominii.local"
LOGIN_ATTEMPTS = int(os.getenv("LOGIN_ATTEMPTS_PER_10_MIN", "10"))
OTP_REQUESTS_PER_HOUR = int(os.getenv("OTP_REQUESTS_PER_HOUR", "5"))
OTP_MAX_TRIES = 5
_dummy_hash_cache = {}


async def _json_object(request: Request) -> dict:
    try:
        data = await request.json()
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(status_code=400, detail="Invalid JSON request body")
    if not isinstance(data, dict):
        raise HTTPException(status_code=400, detail="Request body must be a JSON object")
    return data


def _too_many(wait: int, message: str) -> HTTPException:
    return HTTPException(status_code=429, detail=message, headers={"Retry-After": str(wait)})


def _like_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _dummy_hash() -> str:
    """A real bcrypt hash checked for unknown accounts so timing does not reveal them."""
    if "hash" not in _dummy_hash_cache:
        _dummy_hash_cache["hash"] = get_password_hash("lominii-timing-equaliser")
    return _dummy_hash_cache["hash"]


def _phone_equivalents(raw: str, region: str | None = None) -> list[str]:
    """Stored-format variants of one phone number.

    Canonical E.164, plus the trunk-zero form (+2340803...) that older accounts
    may have been saved with, plus the plain + digits form.
    """
    raw = (raw or "").strip()
    values: list[str] = []

    def add(value):
        if value and value not in values:
            values.append(value)

    try:
        import phonenumbers
    except ImportError:
        phonenumbers = None

    if phonenumbers is not None:
        default_region = None if raw.startswith("+") else (
            region or os.getenv("DEFAULT_PHONE_REGION", "NG")
        ).strip().upper()
        try:
            parsed = phonenumbers.parse(raw, default_region)
        except phonenumbers.NumberParseException:
            parsed = None
        if parsed is not None and phonenumbers.is_possible_number(parsed):
            canonical = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
            add(canonical)
            prefix = "+" + str(parsed.country_code)
            rest = canonical[len(prefix):]
            if rest and not rest.startswith("0"):
                add(prefix + "0" + rest)
    if raw.startswith("+"):
        try:
            add(normalize_phone_uid(raw))
        except ValueError:
            pass
    return values


def _resolve_login_identifier(data: dict) -> tuple[str, str, list[str]]:
    """Work out whether the person typed an email, a phone number or a Lomimail address."""
    region = data.get("country_iso2")
    if region is not None and (not isinstance(region, str) or len(region.strip()) != 2):
        raise HTTPException(status_code=400, detail="country_iso2 must be a two-letter code")

    raw, source = None, None
    for key in ("identifier", "email", "phone", "lomimail_address"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            raw, source = value.strip(), key
            break
    if not raw:
        raise HTTPException(status_code=400, detail="Email, phone number or Lomimail address required")
    if len(raw) > 254:
        raise HTTPException(status_code=400, detail="Identifier is too long")

    if source == "phone" or "@" not in raw:
        candidates = _phone_equivalents(raw, region)
        if not candidates:
            raise HTTPException(status_code=400, detail="Enter a valid phone number, email or Lomimail address")
        return "phone", candidates[0], candidates

    value = raw.lower()
    if value.count("@") == 1 and value.endswith("@" + LOMIMAIL_DOMAIN) and len(value) > len(LOMIMAIL_DOMAIN) + 2:
        return "lomimail", value, []
    if not is_valid_email(value):
        raise HTTPException(status_code=400, detail="Enter a valid phone number, email or Lomimail address")
    return "email", value, []


async def _find_login_user(db, kind: str, value: str, candidates: list[str]):
    if kind == "email":
        statement = select(User).where(User.email == value)
    elif kind == "lomimail":
        statement = select(User).where(func.lower(User.lomimail_address) == value)
    else:
        statement = select(User).where(
            or_(User.phone.in_(candidates), User.lomimail_uid.in_(candidates)),
            User.phone_verified.is_(True),
        )
    users = (await db.execute(statement.limit(2))).scalars().all()
    if len(users) > 1:
        logger.warning("Login identifier matched several accounts (%s)", kind)
        return None
    return users[0] if users else None


async def _user_by_identity(db, identity: str):
    return (await db.execute(select(User).where(User.email == identity))).scalar_one_or_none()


def _mask_phone(phone):
    if not phone:
        return None
    if len(phone) <= 7:
        return "*" * len(phone)
    return phone[:4] + "*" * (len(phone) - 7) + phone[-3:]


def _account_payload(user) -> dict:
    placeholder = (user.email or "").endswith(PLACEHOLDER_EMAIL_SUFFIX)
    return {
        "full_name": user.full_name,
        "email": None if placeholder else user.email,
        "login_identity": user.email,
        "phone": _mask_phone(user.phone),
        "phone_verified": bool(user.phone_verified),
        "lomimail_address": user.lomimail_address,
        "lomimail_startrow": user.lomimail_startrow,
        "country": user.country,
        "state": user.state,
        "lga": user.lga,
        "city": user.city,
        "primary_community_1": user.primary_community_1,
        "primary_community_2": user.primary_community_2,
        "profile_picture_url": user.profile_picture_url,
        "additional_image_url": user.additional_image_url,
        "occupation": user.occupation,
        "language": user.language,
        "has_password": bool(user.password_hash),
        "google_linked": bool(user.google_id),
        "created_at": user.created_at.isoformat() if getattr(user, "created_at", None) else None,
    }


def _validate_bcrypt_password(password: str) -> None:
    """Validate passwords before passing them to bcrypt."""
    if not isinstance(password, str):
        raise HTTPException(status_code=400, detail="Password must be text")
    if len(password) < 6:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 6 characters",
        )
    if len(password.encode("utf-8")) > 72:
        raise HTTPException(
            status_code=400,
            detail="Password is too long; use no more than 72 UTF-8 bytes",
        )


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
    _validate_bcrypt_password(password)
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
    """Sign in with a password and an email, a phone number or a Lomimail address."""
    data = await _json_object(request)
    password = data.get("password", "")
    if not isinstance(password, str) or not password:
        raise HTTPException(status_code=400, detail="Password required")

    kind, value, candidates = _resolve_login_identifier(data)

    throttle_key = f"login:{kind}:{value}"
    wait = ratelimit.check(throttle_key, LOGIN_ATTEMPTS, 600)
    if wait:
        raise _too_many(wait, "Too many sign-in attempts. Try again later.")

    user = await _find_login_user(db, kind, value, candidates)

    # Always verify against a real hash so unknown accounts take the same time.
    stored = user.password_hash if user and user.password_hash else _dummy_hash()
    try:
        password_ok = verify_password(password, stored)
    except Exception:
        password_ok = False

    if not (user and user.password_hash and password_ok):
        if user:
            await record_failure(user.email, db)
        # One message for every failure so accounts cannot be discovered.
        raise HTTPException(status_code=401, detail="Invalid credentials.")

    ratelimit.clear(throttle_key)

    # Preserve the current security level for this token, then reset failures.
    copies = await get_required_copies(user.email, db)
    await reset_failures(user.email, db)

    token = create_bjt(user.email, copies=copies)
    return {
        "access_token": token,
        "token_type": "bearer",
        "email": user.email,
        "full_name": user.full_name,
        "phone": _mask_phone(user.phone),
        "phone_verified": bool(user.phone_verified),
        "lomimail_address": user.lomimail_address,
    }

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
# Google sign-in (the Google ID token is verified on the server)
# ---------------------------------------------------------------------------
GOOGLE_JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"
GOOGLE_ISSUERS = ("accounts.google.com", "https://accounts.google.com")
_google_jwks = {"keys": None, "expires": 0.0, "fetched": 0.0}


def _google_client_ids() -> list[str]:
    return [item.strip() for item in os.getenv("GOOGLE_CLIENT_ID", "").split(",") if item.strip()]


async def _google_signing_keys(force: bool = False) -> list[dict]:
    now = time.time()
    if _google_jwks["keys"] and not force and now < _google_jwks["expires"]:
        return _google_jwks["keys"]
    if _google_jwks["keys"] and force and now - _google_jwks["fetched"] < 60:
        return _google_jwks["keys"]  # do not let random key ids hammer Google
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(5.0, connect=3.0)) as client:
            response = await client.get(GOOGLE_JWKS_URL)
            response.raise_for_status()
            keys = response.json().get("keys") or []
            cache_control = response.headers.get("cache-control", "")
    except Exception as exc:
        logger.warning("Could not fetch Google signing keys: %s", exc)
        if _google_jwks["keys"]:
            return _google_jwks["keys"]
        raise HTTPException(status_code=503, detail="Google sign-in is temporarily unavailable.")
    max_age = 3600
    match = re.search(r"max-age=(\d+)", cache_control)
    if match:
        max_age = max(300, min(int(match.group(1)), 86400))
    _google_jwks.update(keys=keys, expires=now + max_age, fetched=now)
    return keys


def _validate_google_claims(claims: dict) -> dict:
    failed = HTTPException(status_code=401, detail="Google sign-in could not be verified.")
    if claims.get("iss") not in GOOGLE_ISSUERS:
        raise failed
    subject, email = claims.get("sub"), claims.get("email")
    if not isinstance(subject, str) or not subject or not isinstance(email, str) or "@" not in email:
        raise failed
    if claims.get("email_verified") not in (True, "true"):
        raise HTTPException(status_code=401, detail="Your Google email address is not verified.")
    return claims


async def _verify_google_id_token(id_token) -> dict:
    """Verify signature, audience, expiry, issuer and email_verified of a Google ID token."""
    client_ids = _google_client_ids()
    if not client_ids:
        raise HTTPException(status_code=503, detail="Google sign-in is not configured.")
    failed = HTTPException(status_code=401, detail="Google sign-in could not be verified.")
    if not isinstance(id_token, str) or not id_token or len(id_token) > 4096:
        raise failed
    try:
        header = jose_jwt.get_unverified_header(id_token)
    except JWTError:
        raise failed
    if header.get("alg") != "RS256" or not header.get("kid"):
        raise failed

    keys = await _google_signing_keys()
    key = next((item for item in keys if item.get("kid") == header["kid"]), None)
    if key is None:
        keys = await _google_signing_keys(force=True)
        key = next((item for item in keys if item.get("kid") == header["kid"]), None)
    if key is None:
        raise failed

    for audience in client_ids:
        try:
            claims = jose_jwt.decode(
                id_token, key, algorithms=["RS256"], audience=audience,
                options={"leeway": 30},
            )
        except JWTError:
            continue
        return _validate_google_claims(claims)
    raise failed


@router.get("/config")
async def public_config():
    """Public client settings. A Google client ID is public by design."""
    client_ids = _google_client_ids()
    region = os.getenv("DEFAULT_PHONE_REGION", "NG").strip().upper()
    if len(region) != 2 or not region.isalpha():
        region = "NG"
    return {
        "google_client_id": client_ids[0] if client_ids else None,
        "default_phone_region": region,
    }


@router.post("/google")
async def google_auth(request: Request, db: AsyncSession = Depends(get_db)):
    """Sign in with Google. The client sends the ID token (credential); nothing else is trusted."""
    data = await _json_object(request)
    credential = data.get("credential") or data.get("id_token")
    if not isinstance(credential, str) or not credential:
        raise HTTPException(status_code=400, detail="Google ID token required")

    claims = await _verify_google_id_token(credential)
    google_id = claims["sub"]
    email = claims["email"].strip().lower()
    fallback_name = email.split("@")[0]
    full_name = str(
        claims.get("name")
        or " ".join(part for part in (claims.get("given_name"), claims.get("family_name")) if part)
        or fallback_name
    ).strip()[:255] or fallback_name

    user = (await db.execute(select(User).where(User.google_id == google_id))).scalar_one_or_none()
    if user is None:
        existing = await _user_by_identity(db, email)
        if existing is not None:
            if existing.password_hash:
                # Sign-up never verifies email, so a password account is not proof of
                # ownership. Linking must be done from inside that signed-in account.
                raise HTTPException(
                    status_code=409,
                    detail=(
                        "An account with this email already exists. Sign in with your "
                        "password, then link Google from your account settings."
                    ),
                )
            existing.google_id = google_id
            user = existing
        else:
            user = User(email=email, full_name=full_name, google_id=google_id, password_hash="")
            db.add(user)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Could not complete Google sign-in. Please retry.")

    token = create_bjt(user.email)
    return {
        "access_token": token,
        "token_type": "bearer",
        "email": user.email,
        "full_name": user.full_name,
        "lomimail_address": user.lomimail_address,
    }


@router.post("/google/link")
async def google_link(request: Request, email: str = Depends(get_current_user),
                      db: AsyncSession = Depends(get_db)):
    """Attach a Google account to the signed-in account."""
    data = await _json_object(request)
    credential = data.get("credential") or data.get("id_token")
    if not isinstance(credential, str) or not credential:
        raise HTTPException(status_code=400, detail="Google ID token required")

    claims = await _verify_google_id_token(credential)
    user = await _user_by_identity(db, email)
    if user is None:
        raise HTTPException(status_code=404, detail="Account not found")

    other = (await db.execute(select(User).where(User.google_id == claims["sub"]))).scalar_one_or_none()
    if other is not None and other.id != user.id:
        raise HTTPException(status_code=409, detail="This Google account is already linked to another account.")
    if user.google_id and user.google_id != claims["sub"]:
        raise HTTPException(status_code=409, detail="A different Google account is already linked.")

    user.google_id = claims["sub"]
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Could not link Google. Please retry.")
    return {"linked": True, "google_email": claims["email"]}


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

    # Store one canonical form so the same number cannot create two accounts.
    phone = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    return phone, region, country.strip()


def _profile_url(data, key, limit=500):
    """An image URL must be http(s); other schemes (javascript:, data:) are rejected."""
    value = _profile_text(data, key, limit)
    if value is None:
        return None
    parsed = urlparse(value)
    if parsed.scheme not in ("http", "https") or not parsed.netloc or any(ch.isspace() for ch in value):
        raise HTTPException(status_code=400, detail=f"{key} must be a valid http(s) URL.")
    return value


async def _optional_authenticated_user(request: Request, db):
    """The signed-in account if a valid registered-user token was sent, else None."""
    header = request.headers.get("authorization", "")
    if not header.lower().startswith("bearer "):
        return None
    payload = validate_token(header[7:].strip())
    identity = payload.get("sub") if payload else None
    if not isinstance(identity, str) or not identity or identity.startswith("guest-"):
        return None
    return await _user_by_identity(db, identity)


async def _next_lomimail_address(db, full_name: str) -> str:
    """First free address for a name, reading only the names that could collide."""
    local = normalize_lomimail_local_part(full_name)  # ValueError for unusable names
    pattern = f"{_like_escape(local)}%@{LOMIMAIL_DOMAIN}"
    rows = await db.execute(
        select(User.lomimail_address).where(
            func.lower(User.lomimail_address).like(pattern, escape="\\")
        )
    )
    return generate_lomimail_address(full_name, [row[0] for row in rows.all() if row[0]])


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

    wait = ratelimit.check(f"otp-burst:{phone}", 1, 30)
    if wait:
        raise _too_many(wait, "Please wait before requesting another code.")
    wait = ratelimit.check(f"otp-hour:{phone}", OTP_REQUESTS_PER_HOUR, 3600)
    if wait:
        raise _too_many(wait, "Too many code requests for this number. Try again later.")

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
    # PostgreSQL may return a timezone-aware expiry when the existing
    # column is TIMESTAMPTZ, even if the ORM model was declared without tz.
    expiry = otp_record.expires_at
    now = (
        datetime.now(expiry.tzinfo)
        if expiry.tzinfo is not None and expiry.utcoffset() is not None
        else datetime.utcnow()
    )
    if now > expiry:
        raise HTTPException(status_code=400, detail="OTP expired. Request a new code.")
    try_key = f"otp-try:{otp_record.id}"
    wait = ratelimit.check(try_key, OTP_MAX_TRIES, 600)
    if wait:
        # Too many guesses against this code: burn it so it cannot be brute-forced.
        otp_record.verified = True
        try:
            await db.commit()
        except Exception:
            await db.rollback()
        raise _too_many(wait, "Too many incorrect codes. Request a new code.")
    if not hmac.compare_digest(str(otp_record.code), otp_input):
        raise HTTPException(status_code=400, detail="Invalid OTP")
    ratelimit.clear(try_key)

    candidates = _phone_equivalents(phone)
    users = (
        await db.execute(
            select(User).where(
                or_(User.lomimail_uid.in_(candidates), User.phone.in_(candidates))
            )
        )
    ).scalars().all()

    if len(users) > 1:
        raise HTTPException(
            status_code=409,
            detail="This phone matches multiple accounts; reconciliation is required.",
        )

    user = users[0] if users else None

    # A signed-in account can claim a phone number (and its Lomimail identity).
    linked_user = await _optional_authenticated_user(request, db)
    if linked_user is not None:
        if user is not None and user.id != linked_user.id:
            raise HTTPException(
                status_code=409,
                detail="This phone number already belongs to another account.",
            )
        if user is None and linked_user.phone and linked_user.phone not in candidates:
            raise HTTPException(
                status_code=409,
                detail="This account already has a different verified phone number.",
            )
        user = linked_user

    if user is None:
        full_name = data.get("full_name")
        password = data.get("password")

        if not isinstance(full_name, str) or not full_name.strip():
            raise HTTPException(status_code=400, detail="Full name is required.")
        full_name = full_name.strip()

        _validate_bcrypt_password(password)

        state = _profile_text(data, "state", 100, required=True)
        lga = _profile_text(data, "lga", 100, required=True)
        city = _profile_text(data, "city", 100, required=True)
        community1 = _profile_text(
            data, "primary_community_1", 150, required=True
        )
        community2 = _profile_text(data, "primary_community_2", 150)
        picture = _profile_url(data, "profile_picture_url")
        additional_image = _profile_url(data, "additional_image_url")

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
        try:
            # Flush now so uniqueness and database constraints are handled
            # before the rest of the identity handshake proceeds.
            await db.flush()
        except IntegrityError:
            await db.rollback()
            raise HTTPException(
                status_code=409,
                detail=(
                    "An account or identity already exists for this phone. "
                    "Please retry verification or contact support."
                ),
            )
        except Exception:
            await db.rollback()
            raise HTTPException(
                status_code=500,
                detail="Could not create the account during verification.",
            )
    else:
        # Existing accounts keep their established name, password and profile.
        user.phone = phone
        # A Google-only account gets a password so it can also sign in by phone.
        if linked_user is not None and not user.password_hash and data.get("password"):
            _validate_bcrypt_password(data.get("password"))
            user.password_hash = get_password_hash(data.get("password"))

    if not user.lomimail_address:
        try:
            user.lomimail_address = await _next_lomimail_address(db, user.full_name)
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
        # Generate the token before committing so token configuration errors
        # do not leave the OTP consumed while the client receives a 500.
        token = create_bjt(user.email)
        await db.commit()
        await db.refresh(user)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Identity conflict occurred. Please retry verification.",
        )
    except HTTPException:
        await db.rollback()
        raise
    except Exception:
        await db.rollback()
        logger.exception("Unexpected error during phone OTP verification")
        raise HTTPException(
            status_code=500,
            detail="Phone verification could not be completed. Please retry.",
        )

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


# ---------------------------------------------------------------------------
# Account: read and edit the signed-in profile
# ---------------------------------------------------------------------------
PROFILE_TEXT_FIELDS = {
    "state": (100, True),
    "lga": (100, True),
    "city": (100, True),
    "primary_community_1": (150, True),
    "primary_community_2": (150, False),
    "occupation": (100, False),
}


@router.get("/me")
async def me(email: str = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    user = await _user_by_identity(db, email)
    if user is None:
        raise HTTPException(status_code=404, detail="Account not found")
    return _account_payload(user)


@router.put("/profile")
async def update_profile(request: Request, email: str = Depends(get_current_user),
                         db: AsyncSession = Depends(get_db)):
    """Edit profile fields. The Lomimail address and phone are never changed here."""
    data = await _json_object(request)
    user = await _user_by_identity(db, email)
    if user is None:
        raise HTTPException(status_code=404, detail="Account not found")

    changes = {}
    if "full_name" in data:
        name = _profile_text(data, "full_name", 255, required=True)
        if is_blocked(name):
            raise HTTPException(status_code=400, detail="Blocked content")
        changes["full_name"] = name
    for key, (limit, required) in PROFILE_TEXT_FIELDS.items():
        if key in data:
            value = _profile_text(data, key, limit, required=required)
            if value and is_blocked(value):
                raise HTTPException(status_code=400, detail="Blocked content")
            changes[key] = value
    for key in ("profile_picture_url", "additional_image_url"):
        if key in data:
            changes[key] = _profile_url(data, key)
    if "language" in data:
        language = data.get("language")
        if not isinstance(language, str) or language not in SUPPORTED_LANGUAGES:
            raise HTTPException(status_code=400, detail="Unsupported language")
        changes["language"] = language
    if not changes:
        raise HTTPException(status_code=400, detail="Nothing to update")

    for key, value in changes.items():
        setattr(user, key, value)
    try:
        await db.commit()
        await db.refresh(user)
    except Exception:
        await db.rollback()
        logger.exception("Profile update failed")
        raise HTTPException(status_code=500, detail="Could not save the profile. Please retry.")
    return _account_payload(user)
