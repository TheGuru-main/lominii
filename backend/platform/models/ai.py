from uuid import uuid4
from datetime import datetime

from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    DateTime,
    ForeignKey,
    Float,
)

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from platform.database import Base


# ==========================================================
# AI CONVERSATIONS
# ==========================================================

class AIConversation(Base):
    __tablename__ = "ai_conversations"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    workspace = Column(
        String(50),
        nullable=False,
        default="search",
    )

    title = Column(
        String(255),
        nullable=True,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    messages = relationship(
        "AIMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
    )


# ==========================================================
# AI MESSAGES
# ==========================================================

class AIMessage(Base):
    __tablename__ = "ai_messages"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("ai_conversations.id"),
        nullable=False,
        index=True,
    )

    role = Column(
        String(20),
        nullable=False,
    )

    content = Column(
        Text,
        nullable=False,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    conversation = relationship(
        "AIConversation",
        back_populates="messages",
    )


# ==========================================================
# AI MEMORY
# ==========================================================

class AIMemory(Base):
    __tablename__ = "ai_memory"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    memory_type = Column(
        String(50),
        nullable=False,
    )

    title = Column(
        String(255),
        nullable=True,
    )

    content = Column(
        Text,
        nullable=False,
    )

    importance = Column(
        Integer,
        default=1,
    )

    source = Column(
        String(50),
        nullable=True,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


# ==========================================================
# AI KNOWLEDGE
# ==========================================================

class AIKnowledge(Base):
    __tablename__ = "ai_knowledge"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    topic = Column(
        String(255),
        nullable=False,
        index=True,
    )

    summary = Column(
        Text,
        nullable=False,
    )

    source = Column(
        String(255),
        nullable=True,
    )

    confidence = Column(
        Float,
        default=1.0,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    knowledge_type = Column(
        String(50),
        default="general",
        index=True,
    )

    language = Column(
        String(10),
        default="en",
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    access_count = Column(
        Integer,
        default=0,
    )

    last_used = Column(
        DateTime,
        nullable=True,
    )
# ==========================================================
# RELATED SEARCHES
# ==========================================================

class AIRelatedSearch(Base):
    __tablename__ = "ai_related_searches"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    query = Column(
        String(500),
        nullable=False,
        index=True,
    )

    related_query = Column(
        String(500),
        nullable=False,
    )

    score = Column(
        Float,
        default=0.0,
    )

    search_count = Column(
        Integer,
        default=0,
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    source = Column(
        String(50),
        default="search_cache",
    )