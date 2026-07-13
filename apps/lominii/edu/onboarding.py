"""
LOMINII EDU - Onboarding
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from platform.database import get_db
from platform.auth import get_current_user
from platform.models import User
from platform.schemas import (
    StudentOnboardingCreate,
    TeacherOnboardingCreate,
    SchoolOnboardingCreate,
    UniversityOnboardingCreate,
    LibraryOnboardingCreate,
    BookshopOnboardingCreate,
    TrainingInstituteOnboardingCreate,
)

router = APIRouter()