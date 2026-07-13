"""Pydantic schemas for request/response validation"""
from pydantic import BaseModel
from uuid import UUID
from typing import Optional, List, Dict
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
# =========================================================================== ---------------------------------------------------------------------------
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


# Returned by GET /api/edu/curriculum
class CurriculumOut(BaseModel):
    subjects: List[SubjectOut]


# ---------------------------------------------------------------------------
# LESSONS
# ---------------------------------------------------------------------------

class LessonOut(BaseModel):
    id: UUID
    title: str
    content: Optional[str]
    created_at: datetime

    class Config:
        orm_mode = True


# ---------------------------------------------------------------------------
# QUIZZES
# ---------------------------------------------------------------------------

class QuizQuestionOut(BaseModel):
    id: int
    question: str
    options: list[str]


class QuizOut(BaseModel):
    questions: list[QuizQuestionOut]


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
    title: str
    description: Optional[str]
    due_date: Optional[datetime]

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
    name: str
    teacher_id: UUID
    created_at: datetime

    class Config:
        orm_mode = True