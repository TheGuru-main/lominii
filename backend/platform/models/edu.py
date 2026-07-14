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

class Question(Base):
    __tablename__ = "questions"
    __table_args__ = {"schema": "curriculum"}

    id = Column(Integer, primary_key=True, autoincrement=True)

    concept_id = Column(
        Integer,
        ForeignKey("curriculum.concepts.id", ondelete="CASCADE"),
        nullable=False,
    )

    question_text = Column(Text, nullable=False)
    options = Column(JSONB)
    correct_answer = Column(Text)
    difficulty = Column(String(20))
    exam_type = Column(String(20))
    year = Column(Integer)
    tags = Column(JSONB)

    nsid = Column(SmallInteger, default=NSID.EDU)

    concept = relationship(
        "Concept",
        back_populates="questions",
    )


class KnowledgeLink(Base):
    __tablename__ = "knowledge_links"
    __table_args__ = {"schema": "curriculum"}

    id = Column(Integer, primary_key=True, autoincrement=True)

    concept_id_1 = Column(
        Integer,
        ForeignKey("curriculum.concepts.id", ondelete="CASCADE"),
        nullable=False,
    )

    concept_id_2 = Column(
        Integer,
        ForeignKey("curriculum.concepts.id", ondelete="CASCADE"),
        nullable=False,
    )

    relationship = Column(String(50))
    nsid = Column(SmallInteger, default=NSID.EDU)

    concept_one = relationship(
        "Concept",
        foreign_keys=[concept_id_1],
    )

    concept_two = relationship(
        "Concept",
        foreign_keys=[concept_id_2],
    )

# ===========================================================================
# CLASSROOM
# ===========================================================================

class Class(Base):
    __tablename__ = "classes"
    __table_args__ = {"schema": "classroom"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    teacher_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.users.id", ondelete="CASCADE"),
        nullable=False,
    )

    subject_id = Column(
        Integer,
        ForeignKey("curriculum.subjects.id", ondelete="CASCADE"),
        nullable=False,
    )

    name = Column(String(255), nullable=False)

    nsid = Column(SmallInteger, default=NSID.EDU)
    created_at = Column(DateTime, server_default="now()")

    teacher = relationship("User")
    subject = relationship("Subject")

    enrollments = relationship(
        "ClassEnrollment",
        back_populates="classroom",
        cascade="all, delete-orphan",
    )

    lessons = relationship(
        "Lesson",
        back_populates="classroom",
        cascade="all, delete-orphan",
    )


class ClassEnrollment(Base):
    __tablename__ = "class_enrollments"
    __table_args__ = {"schema": "classroom"}

    class_id = Column(
        UUID(as_uuid=True),
        ForeignKey("classroom.classes.id", ondelete="CASCADE"),
        primary_key=True,
    )

    student_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.users.id", ondelete="CASCADE"),
        primary_key=True,
    )

    nsid = Column(SmallInteger, default=NSID.EDU)
    joined_at = Column(DateTime, server_default="now()")

    classroom = relationship(
        "Class",
        back_populates="enrollments",
    )

    student = relationship("User")


class Lesson(Base):
    __tablename__ = "lessons"
    __table_args__ = {"schema": "classroom"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    class_id = Column(
        UUID(as_uuid=True),
        ForeignKey("classroom.classes.id", ondelete="CASCADE"),
        nullable=False,
    )

    concept_id = Column(
        Integer,
        ForeignKey("curriculum.concepts.id", ondelete="CASCADE"),
        nullable=False,
    )

    title = Column(String(255), nullable=False)
    content = Column(Text)

    nsid = Column(SmallInteger, default=NSID.EDU)
    created_at = Column(DateTime, server_default="now()")

    classroom = relationship(
        "Class",
        back_populates="lessons",
    )

    concept = relationship("Concept")

    assignments = relationship(
        "Assignment",
        back_populates="lesson",
        cascade="all, delete-orphan",
    )

    progress = relationship(
        "LessonProgress",
        back_populates="lesson",
        cascade="all, delete-orphan",
    )


class LessonProgress(Base):
    __tablename__ = "lesson_progress"
    __table_args__ = {"schema": "classroom"}

    student_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.users.id", ondelete="CASCADE"),
        primary_key=True,
    )

    lesson_id = Column(
        UUID(as_uuid=True),
        ForeignKey("classroom.lessons.id", ondelete="CASCADE"),
        primary_key=True,
    )

    completed = Column(Boolean, default=False)
    completed_at = Column(DateTime)
    time_spent = Column(Integer, default=0)  # seconds

    nsid = Column(SmallInteger, default=NSID.EDU)

    student = relationship("User")

    lesson = relationship(
        "Lesson",
        back_populates="progress",
    )


class Assignment(Base):
    __tablename__ = "assignments"
    __table_args__ = {"schema": "classroom"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    lesson_id = Column(
        UUID(as_uuid=True),
        ForeignKey("classroom.lessons.id", ondelete="CASCADE"),
        nullable=False,
    )

    title = Column(String(255), nullable=False)
    description = Column(Text)
    due_date = Column(DateTime)

    nsid = Column(SmallInteger, default=NSID.EDU)
    created_at = Column(DateTime, server_default="now()")

    lesson = relationship(
        "Lesson",
        back_populates="assignments",
    )

    submissions = relationship(
        "Submission",
        back_populates="assignment",
        cascade="all, delete-orphan",
    )


class Submission(Base):
    __tablename__ = "submissions"
    __table_args__ = {"schema": "classroom"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    assignment_id = Column(
        UUID(as_uuid=True),
        ForeignKey("classroom.assignments.id", ondelete="CASCADE"),
        nullable=False,
    )

    student_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.users.id", ondelete="CASCADE"),
        nullable=False,
    )

    content = Column(Text)

    nsid = Column(SmallInteger, default=NSID.EDU)
    submitted_at = Column(DateTime, server_default="now()")

    assignment = relationship(
        "Assignment",
        back_populates="submissions",
    )

    student = relationship("User")


# ===========================================================================
# ASSESSMENT
# ===========================================================================

class ConceptMastery(Base):
    __tablename__ = "concept_mastery"
    __table_args__ = {"schema": "assessment"}

    student_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.users.id", ondelete="CASCADE"),
        primary_key=True,
    )

    concept_id = Column(
        Integer,
        ForeignKey("curriculum.concepts.id", ondelete="CASCADE"),
        primary_key=True,
    )

    mastery = Column(Float, default=0.0)

    nsid = Column(SmallInteger, default=NSID.EDU)
    last_practiced = Column(DateTime)

    student = relationship("User")
    concept = relationship("Concept")


class QuestionLog(Base):
    __tablename__ = "question_logs"
    __table_args__ = {"schema": "assessment"}

    id = Column(Integer, primary_key=True, autoincrement=True)

    student_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.users.id", ondelete="CASCADE"),
        nullable=False,
    )

    question_id = Column(
        Integer,
        ForeignKey("curriculum.questions.id", ondelete="CASCADE"),
        nullable=False,
    )

    chosen_answer = Column(Text)
    is_correct = Column(Boolean)

    nsid = Column(SmallInteger, default=NSID.EDU)
    answered_at = Column(DateTime, server_default="now()")

    student = relationship("User")
    question = relationship("Question")