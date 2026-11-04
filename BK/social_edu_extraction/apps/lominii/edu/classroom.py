from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from platform.database import get_db
from platform.auth import get_current_user

from platform.models import (
    Class,
    ClassEnrollment,
)

from platform.schemas import (
    ClassCreate,
    ClassOut,
)

router = APIRouter()


@router.post(
    "",
    response_model=ClassOut,
    summary="Create classroom",
)
async def create_classroom(
    payload: ClassCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Teacher creates a classroom.
    """

    classroom = Class(
        teacher_id=current_user.id,
        subject_id=payload.subject_id,
        name=payload.name,
    )

    db.add(classroom)

    await db.commit()

    await db.refresh(classroom)

    return classroom


@router.get(
    "",
    response_model=list[ClassOut],
    summary="Teacher classrooms",
)
async def get_teacher_classrooms(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Return all classrooms owned by the teacher.
    """

    result = await db.execute(
        select(Class)
        .where(
            Class.teacher_id == current_user.id
        )
        .order_by(Class.created_at.desc())
    )

    return result.scalars().all()


@router.post(
    "/{class_id}/join",
    summary="Join classroom",
)
async def join_classroom(
    class_id,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Student joins a classroom.
    """

    classroom = await db.get(Class, class_id)

    if classroom is None:
        raise HTTPException(
            status_code=404,
            detail="Classroom not found.",
        )

    exists = await db.get(
        ClassEnrollment,
        {
            "class_id": class_id,
            "student_id": current_user.id,
        },
    )

    if exists:
        raise HTTPException(
            status_code=400,
            detail="Already enrolled.",
        )

    enrollment = ClassEnrollment(
        class_id=class_id,
        student_id=current_user.id,
    )

    db.add(enrollment)

    await db.commit()

    return {
        "message": "Successfully joined classroom."
    }