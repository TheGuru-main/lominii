"""LOMINII Social Room – Router (complete: feed, likes, profile, news, chat)"""

from fastapi import APIRouter, Depends, HTTPException, Request
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from platform.database import get_db
from platform.auth import get_current_user
from datetime import datetime, timedelta
from platform.content_filter import is_blocked
from platform.models import (
    User, Follow, Post, Comment, Like, NewsSubscription, Status
)
from .messages import router as messages_router
from .follows import router as follows_router



router = APIRouter(prefix="/api/social", tags=["Social"])



router.include_router(messages_router)
router.include_router(follows_router)

 ═══════════════════════════════════════════════════════════
# PROFILE
# ═══════════════════════════════════════════════════════════
@router.get("/profile/{uid}")
async def get_profile(uid: str, db: AsyncSession = Depends(get_db)):
    user = (await db.execute(select(User).where(User.id == uid))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    posts = (await db.execute(
        select(Post).where(Post.author_id == user.id).order_by(Post.created_at.desc()).limit(20)
    )).scalars().all()
    return {
        "full_name": user.full_name,
        "creator_role": user.creator_role,
        "news_category": user.news_category,
        "posts": [{"id": str(p.id), "content": p.content, "created_at": p.created_at.isoformat()} for p in posts]
    }

# ═══════════════════════════════════════════════════════════
# NEWSLETTER SUBSCRIPTIONS (unchanged)
# ═══════════════════════════════════════════════════════════
@router.post("/news/subscribe")
async def subscribe_category(request: Request, email: str = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    data = await request.json()
    category = data.get("category", "").strip().lower()
    if not category:
        raise HTTPException(status_code=400, detail="Missing category")
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    existing = (await db.execute(
        select(NewsSubscription).where(NewsSubscription.user_id == user.id, NewsSubscription.category == category)
    )).scalar_one_or_none()
    if existing:
        return {"status": "already_subscribed"}
    sub = NewsSubscription(user_id=user.id, category=category)
    db.add(sub)
    await db.commit()
    return {"status": "subscribed"}

@router.delete("/news/subscribe")
async def unsubscribe_category(request: Request, email: str = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    data = await request.json()
    category = data.get("category", "").strip().lower()
    if not category:
        raise HTTPException(status_code=400, detail="Missing category")
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    sub = (await db.execute(
        select(NewsSubscription).where(NewsSubscription.user_id == user.id, NewsSubscription.category == category)
    )).scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Not subscribed")
    await db.delete(sub)
    await db.commit()
    return {"status": "unsubscribed"}

@router.get("/news/subscriptions")
async def my_subscriptions(email: str = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    subs = (await db.execute(select(NewsSubscription).where(NewsSubscription.user_id == user.id))).scalars().all()
    return [s.category for s in subs]

# ═══════════════════════════════════════════════════════════
# lomiNews FEED (uses Newscaster role)
# ═══════════════════════════════════════════════════════════

@router.get("/news")
async def news_feed(
    category: str = None,
    country: str = None,
    db: AsyncSession = Depends(get_db)
):
    """Return posts from newscasters, optionally filtered by category."""
    query = select(Post).join(User, Post.author_id == User.id).where(User.creator_role == "newscaster")
    if category:
        query = query.where(User.news_category == category)
    query = query.order_by(Post.created_at.desc()).limit(50)
    posts = (await db.execute(query)).scalars().all()
    return [
        {
            "id": str(p.id),
            "content": p.content,
            "author_id": str(p.author_id),
            "created_at": p.created_at.isoformat()
        }
        for p in posts
    ]

# ═══════════════════════════════════════════════════════════
# STATUS UPDATE 
# ═══════════════════════════════════════════════════════════

@router.get("/status/friends")
async def status_friends(
    email: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    user = (await db.execute(select(User).where(User.email == email))).scalar_one()
    # get followed users
    follows = (await db.execute(select(Follow).where(Follow.follower_id == user.id))).scalars().all()
    friend_uids = [f.followee_id for f in follows]
    if not friend_uids:
        return {"friends": []}
    # get active statuses
    now = datetime.utcnow()
    active = (await db.execute(
        select(Status).where(
            Status.creator_id.in_(friend_uids),
            Status.expires_at > now
        ).order_by(Status.created_at.desc())
    )).scalars().all()
    # Build response with friend names
    friend_map = {}
    if active:
        creator_ids = list(set(s.creator_id for s in active))
        users = (await db.execute(select(User).where(User.id.in_(creator_ids)))).scalars().all()
        friend_map = {u.id: u.full_name for u in users}
    return {"friends": [
        {
            "uid": str(s.creator_id),
            "name": friend_map.get(s.creator_id, "Unknown"),
            "media_type": s.media_type,
            "expires_at": s.expires_at.isoformat()
        }
        for s in active
    ]}

@router.get("/status/friend/{uid}")
async def status_friend(
    uid: str,
    email: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    now = datetime.utcnow()
    statuses = (await db.execute(
        select(Status).where(
            Status.creator_id == uid,
            Status.expires_at > now
        ).order_by(Status.created_at.desc())
    )).scalars().all()
    return {"statuses": [
        {
            "media_type": s.media_type,
            "content": s.content,
            "expires_at": s.expires_at.isoformat()
        }
        for s in statuses
    ]}

@router.post("/status")
async def create_status(
    request: Request,
    email: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    data = await request.json()
    user = (await db.execute(select(User).where(User.email == email))).scalar_one()
    media_type = data.get("media_type", "text")
    content = data.get("content", "").strip()
    lifespan_hours = int(data.get("lifespan_hours", 24))
    if not content:
        raise HTTPException(status_code=400, detail="Content cannot be empty")
    if is_blocked(content):
        raise HTTPException(status_code=400, detail="Blocked content")
    expires_at = datetime.utcnow() + timedelta(hours=lifespan_hours)
    status = Status(
        creator_id=user.id,
        media_type=media_type,
        content=content,
        expires_at=expires_at
    )
    db.add(status)
    await db.commit()
    return {"status": "created", "id": str(status.id)}