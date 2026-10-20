from pathlib import Path
from datetime import datetime, timedelta
import shutil

p = Path("apps/lominii/auth/router.py")
s = p.read_text()

start = s.find('@router.post("/phone/request")')
end = s.find('@router.get("/failure-count")', start)

if start < 0 or end < 0:
    raise SystemExit("STOP: Route boundaries not found. No changes made.")

if "def _validate_registration_phone" in s:
    raise SystemExit("STOP: Route patch appears to exist already.")

backup = p.with_name("router.py.pre_profile_registration.bak")
if not backup.exists():
    shutil.copy2(p, backup)
    print("Backup created:", backup)
else:
    print("Existing backup preserved:", backup)

routes = r'''
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

    if not sent:
        raise HTTPException(status_code=502, detail="OTP delivery failed. Request a new code.")

    return {
        "message": "OTP sent successfully",
        "phone": phone,
        "country": country,
        "country_iso2": region,
        "expires_in_seconds": 300,
    }


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


'''

p.write_text(s[:start] + routes + s[end:])
print("SUCCESS: OTP routes updated.")
