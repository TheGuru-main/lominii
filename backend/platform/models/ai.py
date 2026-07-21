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

    is_archived = Column(Boolean, default=False)

    model = Column(String(100), nullable=True)


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

    tokens = Column(Integer, default=0)

    latency_ms = Column(Integer, default=0)

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



# ==========================================================
# AI SUMMARY INDEX
# ==========================================================

class AISummaryIndex(Base):
    __tablename__ = "ai_summary_index"


    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    cache_key = Column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
    )

    query_hash = Column(
        String(64),
        nullable=False,
        index=True,
    )

    normalized_query = Column(
        Text,
        nullable=False,
        index=True,
    )

    domain = Column(
        String(100),
        nullable=False,
        index=True,
    )

    language = Column(
        String(20),
        default="en",
        nullable=False,
    )



    # -----------------------------
    # GSP Identity
    # -----------------------------

    L = Column(
        Integer,
        nullable=False,
    )

    S = Column(
        Integer,
        nullable=False,
        index=True,
    )

    c = Column(
        Integer,
        nullable=False,
        default=0,
    )

    primary_column = Column(
        String(2),
        nullable=False,
    )

    primary_row = Column(
        Integer,
        nullable=False,
    )



    # -----------------------------
    # AI Versioning
    # -----------------------------

    model_version = Column(
        String(50),
        nullable=True,
    )

    summary_version = Column(
        Integer,
        default=1,
    )

    # -----------------------------
    # Usage Statistics
    # -----------------------------

    access_count = Column(
        Integer,
        default=0,
    )

    last_accessed = Column(
        DateTime,
        nullable=True,
    )


    # -----------------------------
    # Timestamps
    # -----------------------------

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