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
    Reactions,
)

from platform.schemas import LikeOut
from platform.nsid import NSID


router = APIRouter(
    prefix="/reactions"
    tags=["Social Reactions"],
)



@router.post("/{post_id}", response_model=LikeOut)
async def like_post(
    post_id: UUID,
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

    post = await db.get(Post, post_id)

    if not post:
        raise HTTPException(
            status_code=404,
            detail="Post not found.",
        )

    existing = await db.scalar(
        select(Like).where(
            Like.post_id == post.id,
            Like.user_id == profile.id,
        )
    )

    if existing:
        return existing

    like = Like(
        post_id=post.id,
        user_id=profile.id,
        nsid=NSID.SOCIAL,
    )

    db.add(like)
    await db.commit()
    await db.refresh(like)

    return like


@router.delete("/{post_id}")
async def unlike_post(
    post_id: UUID,
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

    like = await db.scalar(
        select(Like).where(
            Like.post_id == post_id,
            Like.user_id == profile.id,
        )
    )

    if not like:
        raise HTTPException(
            status_code=404,
            detail="Like not found.",
        )

    await db.delete(like)
    await db.commit()

    return {
        "message": "Post unliked successfully."
    }