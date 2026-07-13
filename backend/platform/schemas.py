"""Pydantic schemas for request/response validation"""
from pydantic import BaseModel
from typing import Optional
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


# ==========================================================
# EDU
# ==========================================================

class SubjectOut(BaseModel):
    id: UUID
    name: str
    icon: str

    class Config:
        orm_mode = True


class CurriculumOut(BaseModel):
    id: UUID
    subject_id: UUID
    title: str
    description: Optional[str] = None

    class Config:
        orm_mode = True


class LessonOut(BaseModel):
    id: UUID
    subject_id: UUID
    title: str
    content: str
    lesson_date: datetime

    class Config:
        orm_mode = True


class QuizQuestionOut(BaseModel):
    id: UUID
    question: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str


class QuizOut(BaseModel):
    id: UUID
    title: str
    questions: list[QuizQuestionOut]


class QuizSubmitCreate(BaseModel):
    quiz_id: UUID
    answers: dict


class QuizSubmitOut(BaseModel):
    score: int
    total: int
    percentage: float


class MasteryOut(BaseModel):
    subject: str
    percentage: float


class ProgressOut(BaseModel):
    completed_lessons: int
    total_lessons: int
    completed_assignments: int
    total_assignments: int


class AssignmentOut(BaseModel):
    id: UUID
    title: str
    description: str
    due_date: datetime

    class Config:
        orm_mode = True


class AssignmentSubmitCreate(BaseModel):
    assignment_id: UUID
    answer: str


class AssignmentSubmitOut(BaseModel):
    submission_id: UUID
    submitted_at: datetime
    status: str


class ClassroomCreate(BaseModel):
    name: str
    description: Optional[str] = None


class ClassroomOut(BaseModel):
    id: UUID
    name: str
    description: Optional[str]

    class Config:
        orm_mode = True