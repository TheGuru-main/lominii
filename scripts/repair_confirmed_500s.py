from pathlib import Path
from datetime import datetime
import shutil
import sys

ROOT = Path(__file__).resolve().parent.parent
MAIN = ROOT / "backend/main.py"
AUTH = ROOT / "apps/lominii/auth/router.py"
STAMP = datetime.now().strftime("%Y%m%d-%H%M%S")

def backup(path):
    target = path.with_name(path.name + ".backup-" + STAMP)
    shutil.copy2(path, target)
    print(f"Backup: {target.relative_to(ROOT)}")

def replace_once(content, old, new, label):
    count = content.count(old)
    if count != 1:
        raise RuntimeError(
            f"{label}: expected exactly one matching block, found {count}. "
            "No further changes were made to this file."
        )
    return content.replace(old, new, 1)

# ----- Fix 1: migrate older public.users tables before create_all -----
main = MAIN.read_text()

startup_old = '''    async with engine.begin() as connection:
        await connection.execute(text("CREATE SCHEMA IF NOT EXISTS news"))
        await connection.execute(text("CREATE SCHEMA IF NOT EXISTS search"))
        await connection.execute(text("CREATE SCHEMA IF NOT EXISTS game"))
        await connection.execute(text("CREATE SCHEMA IF NOT EXISTS messaging"))
        await connection.execute(text("CREATE SCHEMA IF NOT EXISTS crawler"))
        await connection.run_sync(Base.metadata.create_all)
'''

startup_new = '''    async with engine.begin() as connection:
        await connection.execute(text("CREATE SCHEMA IF NOT EXISTS news"))
        await connection.execute(text("CREATE SCHEMA IF NOT EXISTS search"))
        await connection.execute(text("CREATE SCHEMA IF NOT EXISTS game"))
        await connection.execute(text("CREATE SCHEMA IF NOT EXISTS messaging"))
        await connection.execute(text("CREATE SCHEMA IF NOT EXISTS crawler"))

        # Idempotent compatibility migration for existing user tables.
        # create_all() creates missing tables but does not add missing columns.
        await connection.execute(text("CREATE TABLE IF NOT EXISTS public.users ("
            "id UUID PRIMARY KEY, email VARCHAR(255) UNIQUE NOT NULL, "
            "full_name VARCHAR(255) NOT NULL, password_hash VARCHAR(255) NOT NULL)"))

        user_column_migrations = [
            "ALTER TABLE public.users ADD COLUMN IF NOT EXISTS google_id VARCHAR(255)",
            "ALTER TABLE public.users ADD COLUMN IF NOT EXISTS phone VARCHAR(20)",
            "ALTER TABLE public.users ADD COLUMN IF NOT EXISTS country VARCHAR(100)",
            "ALTER TABLE public.users ADD COLUMN IF NOT EXISTS state VARCHAR(100)",
            "ALTER TABLE public.users ADD COLUMN IF NOT EXISTS lga VARCHAR(100)",
            "ALTER TABLE public.users ADD COLUMN IF NOT EXISTS city VARCHAR(100)",
            "ALTER TABLE public.users ADD COLUMN IF NOT EXISTS primary_community_1 VARCHAR(150)",
            "ALTER TABLE public.users ADD COLUMN IF NOT EXISTS primary_community_2 VARCHAR(150)",
            "ALTER TABLE public.users ADD COLUMN IF NOT EXISTS profile_picture_url VARCHAR(500)",
            "ALTER TABLE public.users ADD COLUMN IF NOT EXISTS additional_image_url VARCHAR(500)",
            "ALTER TABLE public.users ADD COLUMN IF NOT EXISTS lomimail_address VARCHAR(255)",
            "ALTER TABLE public.users ADD COLUMN IF NOT EXISTS lomimail_uid VARCHAR(20)",
            "ALTER TABLE public.users ADD COLUMN IF NOT EXISTS phone_verified BOOLEAN NOT NULL DEFAULT FALSE",
            "ALTER TABLE public.users ADD COLUMN IF NOT EXISTS lomimail_handshake_at TIMESTAMP WITHOUT TIME ZONE",
            "ALTER TABLE public.users ADD COLUMN IF NOT EXISTS lomimail_startrow SMALLINT",
            "ALTER TABLE public.users ADD COLUMN IF NOT EXISTS occupation VARCHAR(100)",
            "ALTER TABLE public.users ADD COLUMN IF NOT EXISTS language VARCHAR(10) DEFAULT 'en'",
            "ALTER TABLE public.users ADD COLUMN IF NOT EXISTS news_preferences JSON",
            "ALTER TABLE public.users ADD COLUMN IF NOT EXISTS subscription_status VARCHAR(20) DEFAULT 'free'",
            "ALTER TABLE public.users ADD COLUMN IF NOT EXISTS role VARCHAR(20) DEFAULT 'user'",
            "ALTER TABLE public.users ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now()",
        ]
        for migration_sql in user_column_migrations:
            await connection.execute(text(migration_sql))

        await connection.run_sync(Base.metadata.create_all)
'''

updated_main = replace_once(
    main, startup_old, startup_new, "backend/main.py startup"
)

# ----- Fix 2: compare OTP expiry using compatible datetime awareness -----
auth = AUTH.read_text()

otp_old = '''    if datetime.utcnow() > otp_record.expires_at:
        raise HTTPException(status_code=400, detail="OTP expired. Request a new code.")
'''

otp_new = '''    # PostgreSQL may return a timezone-aware expiry when the existing
    # column is TIMESTAMPTZ, even if the ORM model was declared without tz.
    expiry = otp_record.expires_at
    now = (
        datetime.now(expiry.tzinfo)
        if expiry.tzinfo is not None and expiry.utcoffset() is not None
        else datetime.utcnow()
    )
    if now > expiry:
        raise HTTPException(status_code=400, detail="OTP expired. Request a new code.")
'''

updated_auth = replace_once(auth, otp_old, otp_new, "OTP expiry comparison")

# Validate both edits before writing either file.
compile(updated_main, str(MAIN), "exec")
compile(updated_auth, str(AUTH), "exec")

backup(MAIN)
backup(AUTH)
MAIN.write_text(updated_main)
AUTH.write_text(updated_auth)

print("Updated: backend/main.py")
print("Updated: apps/lominii/auth/router.py")
print("Both edited Python files passed syntax compilation.")
