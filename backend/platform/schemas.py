"""Pydantic schemas for request/response validation"""
from pydantic import BaseModel
from typing import Optional, List, Dict
from uuid import UUID
from datetime import datetime


# ==========================================================
# Messaging
# ==========================================================

class MessageCreate(BaseModel):
    recipient_id: UUID
    body: str
    media_url: Optional[str] = None
    reply_to_id: Optional[UUID] = None


class MessageOut(BaseModel):
    id: UUID
    sender_id: UUID
    recipient_id: UUID
    sender_cell: str
    conversation_cell: str
    body: Optional[str]
    media_url: Optional[str]
    reply_to_id: Optional[UUID]
    is_edited: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        orm_mode = True

# ===========================================================================
# EDU SCHEMAS
# ========================================================================== ---------------------------------------------------------------------------
# CURRICULUM
# ---------------------------------------------------------------------------

class ConceptOut(BaseModel):
    id: int
    name: str

    class Config:
        orm_mode = True


class SubtopicOut(BaseModel):
    id: int
    name: str
    concepts: List[ConceptOut] = []

    class Config:
        orm_mode = True


class TopicOut(BaseModel):
    id: int
    name: str
    subtopics: List[SubtopicOut] = []

    class Config:
        orm_mode = True


class SubjectOut(BaseModel):
    id: int
    name: str
    topics: List[TopicOut] = []

    class Config:
        orm_mode = True


class SubjectListOut(BaseModel):
    subjects: List[SubjectOut]


class CurriculumOut(BaseModel):
    subjects: List[SubjectOut]


# ---------------------------------------------------------------------------
# LESSONS
# ---------------------------------------------------------------------------

class LessonOut(BaseModel):
    id: UUID
    class_id: UUID
    concept_id: int
    title: str
    content: Optional[str] = None
    created_at: datetime

    class Config:
        orm_mode = True


class TodayLessonOut(BaseModel):
    lesson: LessonOut


# ---------------------------------------------------------------------------
# QUIZZES
# ---------------------------------------------------------------------------

class QuizQuestionOut(BaseModel):
    id: int
    question_text: str
    options: List[str]


class QuizOut(BaseModel):
    questions: List[QuizQuestionOut]


class QuizSubmitCreate(BaseModel):
    answers: dict[int, str]


class QuizSubmitOut(BaseModel):
    score: int
    total: int
    percentage: float


# ---------------------------------------------------------------------------
# MASTERY
# ---------------------------------------------------------------------------

class MasteryOut(BaseModel):
    concept_id: int
    concept_name: str
    mastery: float


class ProgressOut(BaseModel):
    completed_lessons: int
    total_lessons: int
    completed_assignments: int
    total_assignments: int


# ---------------------------------------------------------------------------
# ASSIGNMENTS
# ---------------------------------------------------------------------------

class AssignmentOut(BaseModel):
    id: UUID
    lesson_id: UUID
    title: str
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    created_at: datetime

    class Config:
        orm_mode = True


class AssignmentSubmitCreate(BaseModel):
    assignment_id: UUID
    content: str


class AssignmentSubmitOut(BaseModel):
    submission_id: UUID
    submitted_at: datetime
    status: str


# ---------------------------------------------------------------------------
# CLASSROOMS
# ---------------------------------------------------------------------------

class ClassCreate(BaseModel):
    subject_id: int
    name: str


class ClassOut(BaseModel):
    id: UUID
    subject_id: int
    teacher_id: UUID
    name: str
    created_at: datetime

    class Config:
        orm_mode = True


class EnrollmentOut(BaseModel):
    class_id: UUID
    student_id: UUID
    joined_at: datetime

    class Config:
        orm_mode = True