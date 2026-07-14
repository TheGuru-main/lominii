import uuid

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    JSON,
)

from sqlalchemy.dialects.postgresql import UUID
from platform.database import Base


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