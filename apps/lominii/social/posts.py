from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from platform.auth import get_current_user
from platform.content_filter import is_blocked
from platform.database import get_db
from platform.models.public import User
from platform.models.social import (
    Follow,
    Post,
    Comment,
    Like,
)
from platform.nsid import NSID

router = APIRouter(
    prefix="/posts",
    tags=["Social - Posts"]
)

# ═══════════════════════════════════════════════════════════
# CREATE POST
# ═══════════════════════════════════════════════════════════

@router.post("")
async def create_post(
    request: Request,
    email: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    data = await request.json()
    content = data.get("content", "").strip()

    if not content or is_blocked(content):
        raise HTTPException(status_code=400, detail="Invalid or blocked content")

    author = (
        await db.execute(
            select(User).where(User.email == email)
        )
    ).scalar_one_or_none()

    if not author:
        raise HTTPException(status_code=404, detail="User not found")

    post = Post(
        author_id=author.id,
        content=content,
        nsid=NSID.SOCIAL
    )

    db.add(post)
    await db.commit()
    await db.refresh(post)

    return {
        "post_id": str(post.id),
        "author_id": str(author.id),
        "created_at": post.created_at.isoformat()
    }


# ═══════════════════════════════════════════════════════════
# COMMENTS
# ═══════════════════════════════════════════════════════════

@router.post("/comment")
async def add_comment(
    request: Request,
    email: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    data = await request.json()

    post_id = data.get("post_id")
    content = data.get("content", "").strip()

    if not post_id or not content or is_blocked(content):
        raise HTTPException(status_code=400, detail="Invalid input")

    author = (
        await db.execute(
            select(User).where(User.email == email)
        )
    ).scalar_one_or_none()

    post = (
        await db.execute(
            select(Post).where(Post.id == post_id)
        )
    ).scalar_one_or_none()

    if not author or not post:
        raise HTTPException(status_code=404, detail="Not found")

    comment = Comment(
        post_id=post.id,
        author_id=author.id,
        content=content,
        nsid=NSID.SOCIAL
    )

    db.add(comment)
    await db.commit()
    await db.refresh(comment)

    return {
        "comment_id": str(comment.id),
        "author_id": str(author.id),
        "created_at": comment.created_at.isoformat()
    }


# ═══════════════════════════════════════════════════════════
# LIKES
# ═══════════════════════════════════════════════════════════

@router.post("/like")
async def like_post(
    request: Request,
    email: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    data = await request.json()

    post_id = data.get("post_id")

    if not post_id:
        raise HTTPException(status_code=400, detail="Missing post_id")

    user = (
        await db.execute(
            select(User).where(User.email == email)
        )
    ).scalar_one_or_none()

    post = (
        await db.execute(
            select(Post).where(Post.id == post_id)
        )
    ).scalar_one_or_none()

    if not user or not post:
        raise HTTPException(status_code=404, detail="Not found")

    existing = (
        await db.execute(
            select(Like).where(
                Like.post_id == post.id,
                Like.user_id == user.id
            )
        )
    ).scalar_one_or_none()

    if existing:
        return {"status": "already_liked"}

    like = Like(
        post_id=post.id,
        user_id=user.id,
        nsid=NSID.SOCIAL
    )

    db.add(like)
    await db.commit()

    return {"status": "liked"}


@router.delete("/like")
async def unlike_post(
    request: Request,
    email: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    data = await request.json()

    post_id = data.get("post_id")

    if not post_id:
        raise HTTPException(status_code=400, detail="Missing post_id")

    user = (
        await db.execute(
            select(User).where(User.email == email)
        )
    ).scalar_one_or_none()

    post = (
        await db.execute(
            select(Post).where(Post.id == post_id)
        )
    ).scalar_one_or_none()

    if not user or not post:
        raise HTTPException(status_code=404, detail="Not found")

    like = (
        await db.execute(
            select(Like).where(
                Like.post_id == post.id,
                Like.user_id == user.id
            )
        )
    ).scalar_one_or_none()

    if not like:
        raise HTTPException(status_code=404, detail="Not liked")

    await db.delete(like)
    await db.commit()

    return {"status": "unliked"}


# ═══════════════════════════════════════════════════════════
# SOCIAL FEED
# ═══════════════════════════════════════════════════════════

@router.get("/feed")
async def social_feed(
    email: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    user = (
        await db.execute(
            select(User).where(User.email == email)
        )
    ).scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    followed = (
        await db.execute(
            select(Follow.followee_id).where(
                Follow.follower_id == user.id
            )
        )
    ).scalars().all()

    author_ids = list(followed) + [user.id]

    posts = (
        await db.execute(
            select(Post)
            .where(Post.author_id.in_(author_ids))
            .order_by(Post.created_at.desc())
            .limit(50)
        )
    ).scalars().all()

    return [
        {
            "id": str(post.id),
            "author_id": str(post.author_id),
            "content": post.content,
            "created_at": post.created_at.isoformat()
        }
        for post in posts
    ]


# ═══════════════════════════════════════════════════════════
# USER PROFILE
# ═══════════════════════════════════════════════════════════

@router.get("/profile/{uid}")
async def get_profile(
    uid: UUID,
    db: AsyncSession = Depends(get_db)
):
    user = (
        await db.execute(
            select(User).where(User.id == uid)
        )
    ).scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    posts = (
        await db.execute(
            select(Post)
            .where(Post.author_id == user.id)
            .order_by(Post.created_at.desc())
            .limit(20)
        )
    ).scalars().all()

    return {
        "author_id": str(user.id),
        "full_name": user.full_name,
        "creator_role": user.creator_role,
        "news_category": user.news_category,
        "posts": [
            {
                "id": str(post.id),
                "content": post.content,
                "created_at": post.created_at.isoformat()
            }
            for post in posts
        ]
    }