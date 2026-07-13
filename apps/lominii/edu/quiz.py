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