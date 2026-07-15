from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from platform.database import get_db
from platform.auth import get_current_user
from platform.models.public import User
from platform.models.news import NewsSubscription, PrivateNewsFollower
from platform.models.social import (
    SocialProfile,
    Post,
)

from platform.schemas import (
    PostCreate,
    PostOut,
)

from platform.nsid import NSID


      router = APIRouter(
    prefix="/posts",
    tags=["Social Posts"],
)


@router.post("/", response_model=PostOut)
async def create_post(
    payload: PostCreate,
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
            detail="Social profile not found",
        )

    post = Post(
        author_id=profile.id,
        content=payload.content,
        media_urls=payload.media_urls,
        visibility=payload.visibility,
        location=payload.location,
    )

    db.add(post)
    await db.commit()
    await db.refresh(post)

    return post


@router.get("/feed", response_model=list[PostOut])
async def get_feed(
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
            detail="Social profile not found",
        )

    result = await db.execute(
        select(Post)
        .order_by(Post.created_at.desc())
    )

    return result.scalars().all()


@router.get("/{post_id}", response_model=PostOut)
async def get_post(
    post_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    post = await db.get(Post, post_id)

    if not post:
        raise HTTPException(
            status_code=404,
            detail="Post not found",
        )

    return post


@router.get("/user/{profile_id}", response_model=list[PostOut])
async def get_user_posts(
    profile_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Post)
        .where(Post.author_id == profile_id)
        .order_by(Post.created_at.desc())
    )

    return result.scalars().all()


@router.delete("/{post_id}")
async def delete_post(
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
            detail="Social profile not found",
        )

    post = await db.get(Post, post_id)

    if not post:
        raise HTTPException(
            status_code=404,
            detail="Post not found",
        )

    if post.author_id != profile.id:
        raise HTTPException(
            status_code=403,
            detail="You can only delete your own posts.",
        )

    await db.delete(post)
    await db.commit()

    return {"message": "Post deleted successfully"}









