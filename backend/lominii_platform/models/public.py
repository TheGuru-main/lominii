import uuid

from sqlalchemy import (
    Column,
    Integer,
    SmallInteger,
    String,
    Float,
    DateTime,
    ForeignKey,
    Index,
    func,
    Boolean,
    JSON,
    Text,
)

from sqlalchemy.dialects.postgresql import (
    UUID,
    JSONB,
)

from sqlalchemy.orm import relationship
from lominii_platform.database import Base
from lominii_platform.nsid import NSID


# ===========================================================================
# PUBLIC
# ===========================================================================

class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "public"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    email = Column(String(255), unique=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=False)

    google_id = Column(String(255), unique=True)
    phone = Column(String(20), unique=True)

    # Optional profile fields; nullable for legacy-account compatibility.
    country = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    lga = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)
    primary_community_1 = Column(String(150), nullable=True)
    primary_community_2 = Column(String(150), nullable=True)
    profile_picture_url = Column(String(500), nullable=True)
    additional_image_url = Column(String(500), nullable=True)

    # Lomimail identity layer. Nullable for legacy-account compatibility.
    lomimail_address = Column(String(255), nullable=True)
    lomimail_uid = Column(String(20), nullable=True)
    phone_verified = Column(Boolean, nullable=False, default=False, server_default="false")
    lomimail_handshake_at = Column(DateTime, nullable=True)
    lomimail_startrow = Column(SmallInteger, nullable=True)

    occupation = Column(String(100))
    language = Column(String(10), default="en")

    news_preferences = Column(JSON)
    subscription_status = Column(String(20), default="free")
    role = Column(String(20), default="user")

    created_at = Column(DateTime, server_default="now()")


# These indexes enforce identity uniqueness in PostgreSQL and are also
# registered with SQLAlchemy metadata for fresh database initialization.
Index(
    "uq_users_lomimail_address_ci",
    func.lower(User.lomimail_address),
    unique=True,
    postgresql_where=User.lomimail_address.is_not(None),
)
Index(
    "uq_users_lomimail_uid",
    User.lomimail_uid,
    unique=True,
    postgresql_where=User.lomimail_uid.is_not(None),
)


class OTP(Base):
    __tablename__ = "otps"
    __table_args__ = {"schema": "public"}

    id = Column(Integer, primary_key=True, autoincrement=True)

    phone = Column(String(20), nullable=False)
    code = Column(String(6), nullable=False)

    expires_at = Column(DateTime, nullable=False)
    verified = Column(Boolean, default=False)

    created_at = Column(DateTime, server_default="now()")

class BubbleJumboFailure(Base):
    __tablename__ = "bubblejumbo_failures"
    __table_args__ = {"schema": "public"}

    identity = Column(String(255), primary_key=True)
    failures = Column(Integer, default=0)