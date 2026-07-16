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
    Share,
)

from platform.schemas import ShareOut
from platform.nsid import NSID


router = APIRouter(
    prefix="/shares",
    tags=["Social Shares"],
)


@router.post("/{post_id}", response_model=ShareOut)
async def share_post(
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
        select(Share).where(
            Share.post_id == post.id,
            Share.user_id == profile.id,
        )
    )

    if existing:
        return existing

    share = Share(
        post_id=post.id,
        user_id=profile.id,
        nsid=NSID.SOCIAL,
    )

    db.add(share)
    await db.commit()
    await db.refresh(share)

    return share


@router.delete("/{post_id}")
async def unshare_post(
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

    share = await db.scalar(
        select(Share).where(
            Share.post_id == post_id,
            Share.user_id == profile.id,
        )
    )

    if not share:
        raise HTTPException(
            status_code=404,
            detail="Share not found.",
        )

    await db.delete(share)
    await db.commit()

    return {
        "message": "Post unshared successfully."
    }