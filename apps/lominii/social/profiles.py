from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from platform.database import get_db
from platform.auth import get_current_user

from platform.models.public import User
from platform.models.social import (
    SocialProfile,
    Post,
)

from platform.schemas import PostOut


router = APIRouter(
    prefix="/profiles",
    tags=["Social Profiles"],
)


@router.get("/{profile_id}")
async def get_profile(
    profile_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    profile = await db.get(SocialProfile, profile_id)

    if not profile:
        raise HTTPException(
            status_code=404,
            detail="Profile not found.",
        )

    return profile


@router.get("/{profile_id}/posts", response_model=list[PostOut])
async def get_profile_posts(
    profile_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Post)
        .where(Post.author_id == profile_id)
        .order_by(Post.created_at.desc())
    )

    return result.scalars().all()


@router.get("/me")
async def my_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = await db.scalar(
        select(SocialProfile).where(
            SocialProfile.core_user_id == current_user.id
        )
    )

    if not profile:
        raise HTTPException(
            status_code=404,
            detail="Social profile not found.",
        )

    return profile