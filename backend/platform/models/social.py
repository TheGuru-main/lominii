import uuid

from sqlalchemy import (
    Column,
    SmallInteger,
    String,
    DateTime,
    ForeignKey,
    Boolean,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from platform.database import Base
from platform.nsid import NSID

class SocialProfile(Base):
    __tablename__ = "profiles"
    __table_args__ = {"schema": "social"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    core_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.users.id", ondelete="CASCADE"),
        nullable=False,
    )
    social_uid = Column(String(20), unique=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    bio = Column(Text)
    avatar_url = Column(Text)
    location = Column(String)
    nsid = Column(SmallInteger, default=NSID.SOCIAL)
    created_at = Column(DateTime, server_default="now()")

    posts = relationship(
        "Post",
        back_populates="author",
        cascade="all, delete-orphan",
    )

    followers = relationship(
        "Follow",
        foreign_keys="Follow.followee_id",
        back_populates="followee",
        cascade="all, delete-orphan",
    )

    following = relationship(
        "Follow",
        foreign_keys="Follow.follower_id",
        back_populates="follower",
        cascade="all, delete-orphan",
    )