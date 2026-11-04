from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from platform.database import get_db
from platform.auth import get_current_user
from platform.models import Question
from platform.schemas import (
    QuizOut,
    QuizQuestionOut,
    QuizSubmitCreate,
    QuizSubmitOut,
)

router = APIRouter()

@router.get(
    "",
    response_model=QuizOut,
    summary="Get practice quiz"
)
async def get_quiz(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Returns a practice quiz.
    """

    result = await db.execute(
        select(Question).limit(10)
    )

    questions = result.scalars().all()

    return QuizOut(
        questions=[
            QuizQuestionOut(
                id=q.id,
                question=q.question_text,
                options=q.options or []
            )
            for q in questions
        ]
    )

@router.post(
    "/submit",
    response_model=QuizSubmitOut,
    summary="Submit quiz"
)
async def submit_quiz(
    payload: QuizSubmitCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Temporary scoring endpoint.

    Later this endpoint will:

    • store QuestionLog

    • update ConceptMastery

    • update Progress

    • award XP

    • generate recommendations
    """

    total = len(payload.answers)

    score = total

    percentage = (
        score / total * 100
        if total
        else 0
    )

    return QuizSubmitOut(
        score=score,
        total=total,
        percentage=percentage
    )