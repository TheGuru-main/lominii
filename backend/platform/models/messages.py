"""Shared messaging models for the LOMINII platform."""

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
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from platform.database import Base
from platform.nsid import NSID


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = {"schema": "messaging"}

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    sender_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.users.id"),
        nullable=False
    )

    recipient_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.users.id"),
        nullable=False
    )

    sender_cell = Column(
        String(10),
        nullable=False
    )

    conversation_cell = Column(
        String(10),
        nullable=False
    )

    body = Column(Text)

    media_url = Column(Text)

    reply_to_id = Column(
        UUID(as_uuid=True),
        ForeignKey("messaging.messages.id"),
        nullable=True
    )

    is_edited = Column(
        Boolean,
        default=False
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    updated_at = Column(
        DateTime(timezone=True),
        onupdate=func.now()
    )

    deleted_at = Column(
        DateTime(timezone=True),
        nullable=True
    )

    nsid = Column(
        SmallInteger,
        default=NSID.SOCIAL
    )

    sender = relationship(
        "User",
        foreign_keys=[sender_id]
    )

    recipient = relationship(
        "User",
        foreign_keys=[recipient_id]
    )

    reply_to = relationship(
        "Message",
        remote_side=[id]
    )