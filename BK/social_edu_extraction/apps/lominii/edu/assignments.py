from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from platform.database import get_db
from platform.auth import get_current_user

from platform.models import (
    Assignment,
    Submission,
)

from platform.schemas import (
    AssignmentOut,
    AssignmentSubmitCreate,
    AssignmentSubmitOut,
)

router = APIRouter()

@router.get(
    "",
    response_model=list[AssignmentOut],
    summary="Student assignments",
)
async def get_assignments(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Return all assignments.

    Future versions will filter by:
    • student's classrooms
    • enrolled subjects
    • due date
    """

    result = await db.execute(
        select(Assignment)
        .order_by(Assignment.created_at.desc())
    )

    return result.scalars().all()

@router.post(
    "/submit",
    response_model=AssignmentSubmitOut,
    summary="Submit assignment",
)
async def submit_assignment(
    payload: AssignmentSubmitCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Submit an assignment.
    """

    assignment = await db.get(
        Assignment,
        payload.assignment_id,
    )

    if assignment is None:
        raise HTTPException(
            status_code=404,
            detail="Assignment not found.",
        )

    submission = Submission(
        assignment_id=payload.assignment_id,
        student_id=current_user.id,
        content=payload.content,
    )

    db.add(submission)

    await db.commit()

    await db.refresh(submission)

    return AssignmentSubmitOut(
        submission_id=submission.id,
        submitted_at=submission.submitted_at,
        status="submitted",
    )