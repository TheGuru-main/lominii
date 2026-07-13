from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from platform.database import get_db
from platform.auth import get_current_user

from platform.models import (
    Lesson,
    LessonProgress,
    Assignment,
    Submission,
)

from platform.schemas import ProgressOut

router = APIRouter()


@router.get(
    "",
    response_model=ProgressOut,
    summary="Student learning progress",
)
async def get_progress(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Returns the current student's overall learning progress.

    Includes:
    • Completed lessons
    • Total lessons
    • Completed assignments
    • Total assignments

    Future versions may also include:
    • Completion percentage
    • Daily streak
    • Weekly streak
    • XP
    • Mastery score
    • Estimated exam readiness
    """

    # ------------------------------------------------------------
    # Total lessons available
    # ------------------------------------------------------------
    total_lessons = await db.scalar(
        select(func.count()).select_from(Lesson)
    )

    # ------------------------------------------------------------
    # Lessons completed by current student
    # ------------------------------------------------------------
    completed_lessons = await db.scalar(
        select(func.count())
        .select_from(LessonProgress)
        .where(
            LessonProgress.student_id == current_user.id,
            LessonProgress.completed.is_(True),
        )
    )

    # ------------------------------------------------------------
    # Total assignments
    # ------------------------------------------------------------
    total_assignments = await db.scalar(
        select(func.count()).select_from(Assignment)
    )

    # ------------------------------------------------------------
    # Submitted assignments
    # ------------------------------------------------------------
    completed_assignments = await db.scalar(
        select(func.count())
        .select_from(Submission)
        .where(
            Submission.student_id == current_user.id
        )
    )

    # ------------------------------------------------------------
    # Response
    # ------------------------------------------------------------
    return ProgressOut(
        completed_lessons=completed_lessons or 0,
        total_lessons=total_lessons or 0,
        completed_assignments=completed_assignments or 0,
        total_assignments=total_assignments or 0,
    )