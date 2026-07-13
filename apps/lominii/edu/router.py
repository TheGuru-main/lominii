"""
LOMINII EDU Router
Curriculum • Lessons • Quizzes • Mastery • Assignments • Teacher Portal
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from platform.database import get_db
from platform.auth import get_current_user
from platform.nsid import NSID

from platform.models import (
    User,
    Subject,
    Topic,
    Subtopic,
    Concept,
    Question,
    Lesson,
    Assignment,
    Submission,
    Class,
    ClassEnrollment,
    ConceptMastery,
    QuestionLog
)

from platform.schemas import (
    SubjectOut,
    CurriculumOut,
    LessonOut,
    QuizOut,
    QuizSubmitCreate,
    QuizSubmitOut,
    MasteryOut,
    ProgressOut,
    AssignmentOut,
    AssignmentSubmitCreate,
    AssignmentSubmitOut,
    ClassroomCreate,
    ClassroomOut
)

router = APIRouter(
    prefix="/api/edu",
    tags=["Education"]
)

# ==========================================================
# SUBJECTS
# ==========================================================

@router.get("/subjects", response_model=list[SubjectOut])
async def get_subjects(
    db: AsyncSession = Depends(get_db)
):
    """
    Return all curriculum subjects.
    """

    subjects = (
        await db.execute(
            select(Subject)
            .order_by(Subject.name.asc())
        )
    ).scalars().all()

    return [
        SubjectOut(
            id=s.id,
            name=s.name,
            icon="📘"     # temporary default icon
        )
        for s in subjects
    ]