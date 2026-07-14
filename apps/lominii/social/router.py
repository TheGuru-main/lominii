"""LOMINII Social Room – Router (complete: feed, likes, profile, news, chat)"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from platform.database import get_db
from platform.auth import get_current_user
from platform.models import Status
from .messages import router as messages_router
from platform.schemas import MessageCreate, MessageOut
from platform.content_filter import is_blocked
from platform.nsid import NSID
from platform.gsp import calculate_lsum, calculate_ssum, first_letter_index, gsp_place
from platform.models import (
    User, Message, Follow, Post, Comment, Like, NewsSubscription
)

router = APIRouter(prefix="/api/social", tags=["Social"])

router.include_router(messages_router)



# FOLLOWS
# ═══════════════════════════════════════════════════════════

@router.post("/follow")
async def follow_user(request: Request, email: str = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    data = await request.json()
    target_uid = data.get("target_uid")
    if not target_uid:
        raise HTTPException(status_code=400, detail="Missing target_uid")
    follower = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    target = (await db.execute(select(User).where(User.id == target_uid))).scalar_one_or_none()
    if not follower or not target:
        raise HTTPException(status_code=404, detail="User not found")
    existing = (await db.execute(
        select(Follow).where(Follow.follower_id == follower.id, Follow.followee_id == target.id)
    )).scalar_one_or_none()
    if existing:
        return {"status": "already_following"}
    follow = Follow(follower_id=follower.id, followee_id=target.id)
    db.add(follow)
    await db.commit()
    return {"status": "following"}

@router.delete("/follow")
async def unfollow_user(request: Request, email: str = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    data = await request.json()
    target_uid = data.get("target_uid")
    if not target_uid:
        raise HTTPException(status_code=400, detail="Missing target_uid")
    follower = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    target = (await db.execute(select(User).where(User.id == target_uid))).scalar_one_or_none()
    if not follower or not target:
        raise HTTPException(status_code=404, detail="User not found")
    follow = (await db.execute(
        select(Follow).where(Follow.follower_id == follower.id, Follow.followee_id == target.id)
    )).scalar_one_or_none()
    if not follow:
        raise HTTPException(status_code=404, detail="Not following")
    await db.delete(follow)
    await db.commit()
    return {"status": "unfollowed"}

# ═══════════════════════════════════════════════════════════
# POSTS & COMMENTS & LIKES
# ═══════════════════════════════════════════════════════════
@router.post("/post")
async def create_post(request: Request, email: str = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    data = await request.json()
    content = data.get("content", "").strip()
    if not content or is_blocked(content):
        raise HTTPException(status_code=400, detail="Invalid or blocked content")
    author = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if not author:
        raise HTTPException(status_code=404, detail="User not found")
    post = Post(author_id=author.id, content=content)
    db.add(post)
    await db.commit()
    return {"post_id": str(post.id), "created_at": post.created_at.isoformat()}

@router.post("/comment")
async def add_comment(request: Request, email: str = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    data = await request.json()
    post_id = data.get("post_id")
    content = data.get("content", "").strip()
    if not post_id or not content or is_blocked(content):
        raise HTTPException(status_code=400, detail="Invalid input")
    author = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    post = (await db.execute(select(Post).where(Post.id == post_id))).scalar_one_or_none()
    if not author or not post:
        raise HTTPException(status_code=404, detail="Not found")
    comment = Comment(post_id=post.id, author_id=author.id, content=content)
    db.add(comment)
    await db.commit()
    return {"comment_id": str(comment.id), "created_at": comment.created_at.isoformat()}

@router.post("/like")
async def like_post(request: Request, email: str = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    data = await request.json()
    post_id = data.get("post_id")
    if not post_id:
        raise HTTPException(status_code=400, detail="Missing post_id")
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    post = (await db.execute(select(Post).where(Post.id == post_id))).scalar_one_or_none()
    if not user or not post:
        raise HTTPException(status_code=404, detail="Not found")
    existing = (await db.execute(
        select(Like).where(Like.post_id == post.id, Like.user_id == user.id)
    )).scalar_one_or_none()
    if existing:
        return {"status": "already_liked"}
    like = Like(post_id=post.id, user_id=user.id)
    db.add(like)
    await db.commit()
    return {"status": "liked"}

@router.delete("/like")
async def unlike_post(request: Request, email: str = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    data = await request.json()
    post_id = data.get("post_id")
    if not post_id:
        raise HTTPException(status_code=400, detail="Missing post_id")
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    post = (await db.execute(select(Post).where(Post.id == post_id))).scalar_one_or_none()
    if not user or not post:
        raise HTTPException(status_code=404, detail="Not found")
    like = (await db.execute(
        select(Like).where(Like.post_id == post.id, Like.user_id == user.id)
    )).scalar_one_or_none()
    if not like:
        raise HTTPException(status_code=404, detail="Not liked")
    await db.delete(like)
    await db.commit()
    return {"status": "unliked"}

# ═══════════════════════════════════════════════════════════
# GENERAL FEED (friends + own posts)
# ═══════════════════════════════════════════════════════════
@router.get("/feed")
async def social_feed(
    email: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Return posts from users the current user follows, plus their own posts."""
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get list of followed user IDs
    followed = (await db.execute(
        select(Follow.followee_id).where(Follow.follower_id == user.id)
    )).scalars().all()
    # include self to see own posts
    author_ids = list(followed) + [user.id]

    posts = (await db.execute(
        select(Post)
        .where(Post.author_id.in_(author_ids))
        .order_by(Post.created_at.desc())
        .limit(50)
    )).scalars().all()

    # Enrich with author name (simplified; in production join with User)
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