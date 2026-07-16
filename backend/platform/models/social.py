import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    SmallInteger,
    Integer,
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

    id = Column(UUID(as_uuid=True),
    primary_key=True, default=uuid.uuid4)
    core_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.users.id",
    ondelete="CASCADE"),
        nullable=False,)
    social_uid = Column(String(20), unique=True,nullable=False)
    full_name = Column(String(255), nullable=False)
    bio = Column(Text)
    avatar_url = Column(Text)
    location = Column(String)
    nsid = Column(
        SmallInteger,
        default=NSID.SOCIAL)
    created_at = Column(
        DateTime,
        server_default="now()",)
    username = Column(
        String(32),
        unique=True,
        nullable=True,
        index=True,)
    username_verified = Column(
       Boolean,
       default=False,
       nullable=False,)
    username_created_at = Column(
        DateTime,
        nullable=True,)
    posts = relationship(
        "Post",
        back_populates="author",
        cascade="all, delete-orphan",)
    community_posts = relationship(
        "CommunityPost",
        back_populates="author",
        cascade="all, delete-orphan",)
    followers = relationship(
        "Follow",
        foreign_keys="Follow.followee_id",
        back_populates="followee",
        cascade="all, delete-orphan",)
    following = relationship(
        "Follow",
        foreign_keys="Follow.follower_id",
        back_populates="follower",
        cascade="all, delete-orphan",)

class Follow(Base):
    __tablename__ = "follows"
    __table_args__ = {"schema": "social"}

    follower_id = Column(
        UUID(as_uuid=True),
        ForeignKey("social.profiles.id"),
        primary_key=True,)
    followee_id = Column(
        UUID(as_uuid=True),
        ForeignKey("social.profiles.id"),
        primary_key=True,)
    nsid = Column(SmallInteger, default=NSID.SOCIAL)
    created_at = Column(DateTime, server_default="now()")
    follower = relationship(
        "SocialProfile",
        foreign_keys=[follower_id],
        back_populates="following",)
    followee = relationship(
        "SocialProfile",
        foreign_keys=[followee_id],
        back_populates="followers",)


class Post(Base):
    __tablename__ = "posts"
    __table_args__ = {"schema": "social"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    author_id = Column(
        UUID(as_uuid=True),
        ForeignKey("social.profiles.id"),
        nullable=False,)
    content = Column(Text, nullable=False)
    media_urls = Column(JSONB)
    visibility = Column(String(20), default="public")
    location = Column(String)
    nsid = Column(SmallInteger, default=NSID.SOCIAL)
    created_at = Column(DateTime, server_default="now()")
    author = relationship(
        "SocialProfile",
        back_populates="posts",)
    comments = relationship(
        "Comment",
        back_populates="post",
        cascade="all, delete-orphan",)
    likes = relationship(
        "Like",
        back_populates="post",
        cascade="all, delete-orphan",)


class Status(Base):
    __tablename__ = "statuses"
    __table_args__ = {"schema": "social"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    creator_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.users.id", ondelete="CASCADE"),
        nullable=False,)
    media_type = Column(String(10), nullable=False)
    content = Column(Text, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, server_default="now()")


class Comment(Base):
    __tablename__ = "comments"
    __table_args__ = {"schema": "social"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_id = Column(
        UUID(as_uuid=True),
        ForeignKey("social.posts.id", ondelete="CASCADE"),
        nullable=False,)
    author_id = Column(
        UUID(as_uuid=True),
        ForeignKey("social.profiles.id"),
        nullable=False,)
    content = Column(Text, nullable=False)
    nsid = Column(SmallInteger, default=NSID.SOCIAL)
    created_at = Column(DateTime, server_default="now()")
    post = relationship(
        "Post",
        back_populates="comments",)
    author = relationship(
        "SocialProfile",)

class Like(Base):
    __tablename__ = "likes"
    __table_args__ = {"schema": "social"}

    post_id = Column(
        UUID(as_uuid=True),
        ForeignKey("social.posts.id", ondelete="CASCADE"),
        primary_key=True,)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("social.profiles.id"),
        primary_key=True,)
    nsid = Column(SmallInteger, default=NSID.SOCIAL)
    created_at = Column(DateTime, server_default="now()")

    post = relationship(
        "Post",
        back_populates="likes",)
    user = relationship(
        "SocialProfile",)

class Community(Base):
    __tablename__ = "communities"
    __table_args__ = {"schema": "social"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey("social.profiles.id"),
        nullable=False,)
    visibility = Column(
        String(20),
        default="public",
        nullable=False,)
    max_members = Column(
        Integer,
        default=1000,
        nullable=False,)
    nsid = Column(
        SmallInteger,
        default=NSID.SOCIAL,)
    created_at = Column(
        DateTime,
        server_default="now()",)
    members = relationship(
        "CommunityMember",
        back_populates="community",
        cascade="all, delete-orphan",)
    posts = relationship(
        "CommunityPost",
        back_populates="community",
        cascade="all, delete-orphan",)
    bans = relationship(
    "CommunityBan",
    cascade="all, delete-orphan",)

class CommunityMember(Base):
    __tablename__ = "community_members"
    __table_args__ = {"schema": "social"}

    community_id = Column(
        UUID(as_uuid=True),
        ForeignKey("social.communities.id", ondelete="CASCADE"),
        primary_key=True,)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("social.profiles.id"),
        primary_key=True,)
    role = Column(String(20), default="member")
    nsid = Column(SmallInteger, default=NSID.SOCIAL)
    joined_at = Column(DateTime, server_default="now()")

    community = relationship(
        "Community",
        back_populates="members",)
    user = relationship(
        "SocialProfile",)

class PrivacySettings(Base):
    __tablename__ = "privacy_settings"
    __table_args__ = {"schema": "social"}

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.users.id", ondelete="CASCADE"),
        primary_key=True,)
    profile_visibility = Column(String(20), default="public")
    search_visibility = Column(String(20), default="public")
    friend_request_permission = Column(String(20), default="everyone")
    last_seen_visibility = Column(String(20), default="friends")
    nsid = Column(SmallInteger, default=NSID.SOCIAL)
    created_at = Column(DateTime, server_default="now()")
    updated_at = Column(DateTime, server_default="now()")

class FriendRequest(Base):
    __tablename__ = "friend_requests"
    __table_args__ = {"schema": "social"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    sender_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.users.id", ondelete="CASCADE"),
        nullable=False,)
    receiver_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.users.id", ondelete="CASCADE"),
        nullable=False,)
    status = Column(String(20), default="pending")
    nsid =Column(SmallInteger, default=NSID.SOCIAL)
    created_at = Column(DateTime, server_default="now()")
    updated_at = Column(DateTime, server_default="now()")

class BlockedUser(Base):
    __tablename__ = "blocked_users"
    __table_args__ = {"schema": "social"}

    blocker_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.users.id", ondelete="CASCADE"),
        primary_key=True,)
    blocked_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.users.id", ondelete="CASCADE"),
        primary_key=True,)
    nsid = Column(SmallInteger, default=NSID.SOCIAL)
    created_at = Column(DateTime, server_default="now()")

class MutedUser(Base):
    __tablename__ = "muted_users"
    __table_args__ = {"schema": "social"}

    muter_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.users.id", ondelete="CASCADE"),
        primary_key=True,)
    muted_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.users.id", ondelete="CASCADE"),
        primary_key=True,)
    nsid = Column(SmallInteger, default=NSID.SOCIAL)
    created_at = Column(DateTime, server_default="now()")

class CommunityPost(Base):
    __tablename__ = "community_posts"
    __table_args__ = {"schema": "social"}

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,)
    community_id = Column(
        UUID(as_uuid=True),
        ForeignKey("social.communities.id",
ondelete="CASCADE"),
        nullable=False,
        index=True,)
    author_id = Column(
        UUID(as_uuid=True),
        ForeignKey("social.profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,)
    content = Column(
        Text,
        nullable=True,)
    media_urls = Column(
        JSONB,
        default=list,
        nullable=False,)
    nsid = Column(
    SmallInteger,
    default=NSID.SOCIAL,)
    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,)
    deleted_at = Column(
        DateTime,
        nullable=True,)
    is_pinned = Column(
        Boolean,
        default=False,
        nullable=False,)
    is_announcement = Column(
       Boolean,
       default=False,
       nullable=False,)
    community = relationship(
        "Community",
        back_populates="posts",)
    author = relationship(
        "SocialProfile",
        back_populates="community_posts",)

class CommunityBan(Base):
    __tablename__ = "community_bans"
    __table_args__ = {"schema": "social"}

    community_id = Column(
        UUID(as_uuid=True),
        ForeignKey("social.communities.id", ondelete="CASCADE"),
        primary_key=True,)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("social.profiles.id", ondelete="CASCADE"),
        primary_key=True,)
    banned_by = Column(
        UUID(as_uuid=True),
        ForeignKey("social.profiles.id"),
        nullable=False,)
    reason = Column(Text)
    nsid = Column(
        SmallInteger,
        default=NSID.SOCIAL,)
    created_at = Column(
        DateTime,
        server_default="now()",)