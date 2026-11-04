from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from platform.database import get_db
from platform.auth import get_current_user

from platform.models.public import User
from platform.models.social import (
    SocialProfile,
    Follow,
    Post,
    Like,
    Comment,
)

router = APIRouter(
    prefix="/feed",
    tags=["Social Feed"],
)


@router.get("/")
async def social_feed(
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

    followed = (
        await db.execute(
            select(Follow.followee_id).where(
                Follow.follower_id == profile.id
            )
        )
    ).scalars().all()

    author_ids = list(followed) + [profile.id]

    result = await db.execute(
        select(Post)
        .where(Post.author_id.in_(author_ids))
        .order_by(Post.created_at.desc())
        .limit(50)
    )

    posts = result.scalars().all()

    return posts