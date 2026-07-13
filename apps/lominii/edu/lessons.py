from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from platform.database import get_db
from platform.auth import get_current_user
from platform.models import Lesson
from platform.schemas import LessonOut

router = APIRouter()


@router.get(
    "/today",
    response_model=LessonOut,
    summary="Today's lesson"
)
async def get_today_lesson(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Returns the latest lesson.
    Later this will be personalized by:
    - classroom
    - curriculum
    - mastery
    - learning streak
    """

    result = await db.execute(
        select(Lesson)
        .order_by(Lesson.created_at.desc())
        .limit(1)
    )

    lesson = result.scalar_one_or_none()

    if lesson is None:
        raise HTTPException(
            status_code=404,
            detail="No lesson available."
        )

    return lesson