from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from platform.database import get_db
from platform.auth import get_current_user
from platform.content_filter import is_blocked

from platform.models.public import User
from platform.models.social import (
    SocialProfile,
    Post,
    Comment,
)

from platform.schemas import (
    CommentCreate,
    CommentOut,
)

from platform.nsid import NSID


router = APIRouter(
    prefix="/comments",
    tags=["Social Comments"],
)


@router.post("/{post_id}", response_model=CommentOut)
async def add_comment(
    post_id: UUID,
    payload: CommentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if is_blocked(payload.content):
        raise HTTPException(
            status_code=400,
            detail="Comment violates community guidelines.",
        )

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

    comment = Comment(
        post_id=post.id,
        author_id=profile.id,
        content=payload.content,
        nsid=NSID.SOCIAL,
    )

    db.add(comment)
    await db.commit()
    await db.refresh(comment)

    return comment