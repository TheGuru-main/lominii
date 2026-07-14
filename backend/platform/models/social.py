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



class Follow(Base):
    __tablename__ = "follows"
    __table_args__ = {"schema": "social"}

    follower_id = Column(
        UUID(as_uuid=True),
        ForeignKey("social.profiles.id"),
        primary_key=True,
    )

    followee_id = Column(
        UUID(as_uuid=True),
        ForeignKey("social.profiles.id"),
        primary_key=True,
    )

    nsid = Column(SmallInteger, default=NSID.SOCIAL)
    created_at = Column(DateTime, server_default="now()")

    follower = relationship(
        "SocialProfile",
        foreign_keys=[follower_id],
        back_populates="following",
    )

    followee = relationship(
        "SocialProfile",
        foreign_keys=[followee_id],
        back_populates="followers",
    )


class Post(Base):
    __tablename__ = "posts"
    __table_args__ = {"schema": "social"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    author_id = Column(
        UUID(as_uuid=True),
        ForeignKey("social.profiles.id"),
        nullable=False,
    )
    content = Column(Text, nullable=False)
    media_urls = Column(JSONB)
    visibility = Column(String(20), default="public")
    location = Column(String)
    nsid = Column(SmallInteger, default=NSID.SOCIAL)
    created_at = Column(DateTime, server_default="now()")

    author = relationship(
        "SocialProfile",
        back_populates="posts",
    )

    comments = relationship(
        "Comment",
        back_populates="post",
        cascade="all, delete-orphan",
    )

    likes = relationship(
        "Like",
        back_populates="post",
        cascade="all, delete-orphan",
    )


class Status(Base):
    __tablename__ = "statuses"
    __table_args__ = {"schema": "social"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    creator_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.users.id", ondelete="CASCADE"),
        nullable=False,
    )
    media_type = Column(String(10), nullable=False)
    content = Column(Text, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, server_default="now()")