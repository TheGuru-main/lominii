from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
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

ALLOWED_COMMENT_MEDIA = {
    "image",
    "gif",
    "voice",
    "video",
    "file",
}

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
    if payload.content and is_blocked(payload.content):
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

    count = await db.scalar(
        select(func.count())
        .select_from(Comment)
        .where(
            Comment.post_id == post.id,
            Comment.author_id == profile.id,
        )
    )

    if count >= 6:
        raise HTTPException(
            status_code=400,
            detail="Maximum of 6 comments allowed per user on this post.",
        )

    comment = Comment(
    post_id=post.id,
    author_id=profile.id,
    content=payload.content,
    media_type=payload.media_type,
    media_url=payload.media_url,
    duration=payload.duration,
    nsid=NSID.SOCIAL,
)

    if (
        payload.media_type
        and payload.media_type not in ALLOWED_COMMENT_MEDIA
):
    raise HTTPException(
        status_code=400,
        detail="Unsupported comment media.",
    )

    if (
        not payload.content
        and not payload.media_url
):
    raise HTTPException(
        status_code=400,
        detail="Comment cannot be empty.",
    )

    db.add(comment)
    await db.commit()
    await db.refresh(comment)

    return comment

@router.get("/post/{post_id}", response_model=list[CommentOut])
async def get_comments(
    post_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    post = await db.get(Post, post_id)

    if not post:
        raise HTTPException(
            status_code=404,
            detail="Post not found.",
        )

    result = await db.execute(
        select(Comment)
        .where(Comment.post_id == post_id)
        .order_by(Comment.created_at.asc())
    )

    return result.scalars().all()


@router.delete("/{comment_id}")
async def delete_comment(
    comment_id: UUID,
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

    comment = await db.get(Comment, comment_id)

    if not comment:
        raise HTTPException(
            status_code=404,
            detail="Comment not found.",
        )

    if comment.author_id != profile.id:
        raise HTTPException(
            status_code=403,
            detail="You can only delete your own comments.",
        )

    await db.delete(comment)
    await db.commit()

    return {
        "message": "Comment deleted successfully."
    }