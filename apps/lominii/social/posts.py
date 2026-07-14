from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from platform.database import get_db
from platform.auth import get_current_user
from platform.content_filter import is_blocked
from platform.nsid import NSID

from platform.models import (
    User,
    Post,
    Comment,
    Like,
    Follow
)

router = APIRouter(
    prefix="/posts",
    tags=["Social - Posts"]
)