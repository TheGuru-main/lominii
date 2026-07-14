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
# CURRICULUM
# ===========================================================================

class Subject(Base):
    __tablename__ = "subjects"
    __table_args__ = {"schema": "curriculum"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False)
    nsid = Column(SmallInteger, default=NSID.EDU)

    topics = relationship(
        "Topic",
        back_populates="subject",
        cascade="all, delete-orphan",
    )


class Topic(Base):
    __tablename__ = "topics"
    __table_args__ = {"schema": "curriculum"}

    id = Column(Integer, primary_key=True, autoincrement=True)

    subject_id = Column(
        Integer,
        ForeignKey("curriculum.subjects.id", ondelete="CASCADE"),
        nullable=False,
    )

    name = Column(String(255), nullable=False)
    nsid = Column(SmallInteger, default=NSID.EDU)

    subject = relationship(
        "Subject",
        back_populates="topics",
    )

    subtopics = relationship(
        "Subtopic",
        back_populates="topic",
        cascade="all, delete-orphan",
    )


class Subtopic(Base):
    __tablename__ = "subtopics"
    __table_args__ = {"schema": "curriculum"}

    id = Column(Integer, primary_key=True, autoincrement=True)

    topic_id = Column(
        Integer,
        ForeignKey("curriculum.topics.id", ondelete="CASCADE"),
        nullable=False,
    )

    name = Column(String(255), nullable=False)
    nsid = Column(SmallInteger, default=NSID.EDU)

    topic = relationship(
        "Topic",
        back_populates="subtopics",
    )

    concepts = relationship(
        "Concept",
        back_populates="subtopic",
        cascade="all, delete-orphan",
    )


class Concept(Base):
    __tablename__ = "concepts"
    __table_args__ = {"schema": "curriculum"}

    id = Column(Integer, primary_key=True, autoincrement=True)

    subtopic_id = Column(
        Integer,
        ForeignKey("curriculum.subtopics.id", ondelete="CASCADE"),
        nullable=False,
    )

    name = Column(String(255), nullable=False)
    nsid = Column(SmallInteger, default=NSID.EDU)

    subtopic = relationship(
        "Subtopic",
        back_populates="concepts",
    )

    questions = relationship(
        "Question",
        back_populates="concept",
        cascade="all, delete-orphan",
    )