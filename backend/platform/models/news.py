import uuid

from sqlalchemy import (
    Column,
    SmallInteger,
    String,
    DateTime,
    Boolean,
    ForeignKey,
)

from sqlalchemy.dialects.postgresql import UUID

from platform.database import Base
from platform.nsid import NSID


class NewsSubscription(Base):
    __tablename__ = "subscriptions"
    __table_args__ = {"schema": "news"}

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.users.id", ondelete="CASCADE"),
        nullable=False,
    )

    category = Column(
        String(100),
        nullable=False,
    )

    enabled = Column(
        Boolean,
        default=True,
    )

    nsid = Column(
        SmallInteger,
        default=NSID.NEWS,
    )

    created_at = Column(
        DateTime,
        server_default="now()",
    )


class NewsNotification(Base):
    __tablename__ = "notifications"
    __table_args__ = {"schema": "news"}

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.users.id", ondelete="CASCADE"),
        nullable=False,
    )

    title = Column(
        String(255),
        nullable=False,
    )

    body = Column(
        String,
    )

    article_url = Column(
        String,
    )

    is_read = Column(
        Boolean,
        default=False,
    )

    nsid = Column(
        SmallInteger,
        default=NSID.NEWS,
    )

    created_at = Column(
        DateTime,
        server_default="now()",
    )


class PrivateNewsFollower(Base):
    __tablename__ = "private_followers"
    __table_args__ = {"schema": "news"}

    creator_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.users.id", ondelete="CASCADE"),
        primary_key=True,
    )

    follower_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.users.id", ondelete="CASCADE"),
        primary_key=True,
    )

    nsid = Column(
        SmallInteger,
        default=NSID.NEWS,
    )

    created_at = Column(
        DateTime,
        server_default="now()",
    )