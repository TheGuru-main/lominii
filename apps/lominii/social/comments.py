from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from platform.database import get_db
from platform.auth import get_current_user
from platform.content_filter import is_blocked

from platform.models.public import User
from platform.models.social import (
    SocialProfile,
    Post,
    Comment,
)

from platform.nsid import NSID


router = APIRouter(
    prefix="/comments",
    tags=["Social Comments"],
)