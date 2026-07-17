import uuid

from sqlalchemy import (
    Column,
    Integer,
    SmallInteger,
    String,
    Float,
    DateTime,
    ForeignKey,
    Boolean,
    JSON,
    Text,
)

from sqlalchemy.dialects.postgresql import (
    UUID,
    JSONB,
)

from sqlalchemy.orm import relationship

from platform.database import Base
from platform.nsid import NSID


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

    occupation = Column(String(100))
    language = Column(String(10), default="en")

    news_preferences = Column(JSON)
    subscription_status = Column(String(20), default="free")
    role = Column(String(20), default="user")

    created_at = Column(DateTime, server_default="now()")


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