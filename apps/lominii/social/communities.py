from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from uuid import UUID

from platform.database import get_db
from platform.auth import get_current_user

from platform.models.public import User
from platform.models.social import (
    SocialProfile,
    Community,
    CommunityMember,
)

router = APIRouter(
    prefix="/communities",
    tags=["Social Communities"],
)