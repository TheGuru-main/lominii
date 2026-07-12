"""LOMINII Social Room – Router (complete: feed, likes, profile, news, chat)"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from platform.database import get_db
from platform.auth import get_current_user
from platform.schemas import MessageCreate, MessageOut
from platform.content_filter import is_blocked
from platform.nsid import NSID
from platform.gsp import calculate_lsum, calculate_ssum, first_letter_index, gsp_place
from platform.models import (
    User, Message, Follow, Post, Comment, Like, NewsSubscription
)

router = APIRouter(prefix="/api/social", tags=["Social"])

# ═══════════════════════════════════════════════════════════
# MESSAGING (aligned with real Message model)
# ═══════════════════════════════════════════════════════════

@router.post("/messages/send", response_model=MessageOut)
async def send_message(
    payload: MessageCreate,   # FastAPI validates the incoming JSON automatically
    email: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)

):
    data = await request.json()
    recipient_uid = data.get("recipient_uid")    # core UID of the recipient
    body = data.get("body", "").strip()
    if not recipient_uid or not body:
        raise HTTPException(status_code=400, detail="Missing recipient_uid or body")
    if is_blocked(body):
        raise HTTPException(status_code=400, detail="Blocked content")

    # Look up both users
    sender = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    recipient = (await db.execute(select(User).where(User.id == recipient_uid))).scalar_one_or_none()
    if not sender or not recipient:
        raise HTTPException(status_code=404, detail="User not found")

    # Compute GSP cells (sender's point‑node and a deterministic conversation cell)
    sender_L = calculate_lsum(sender.full_name)
    sender_S = calculate_ssum(sender.full_name)
    sender_c = first_letter_index(sender.full_name)
    sender_primary = gsp_place(sender_L, sender_S, sender_c, K=1)["primary_cell"]
    sender_cell_str = f"{sender_primary['col']},{sender_primary['row']}"

    # Conversation cell = a cell derived from both users (deterministic for the pair)
    conv_L = calculate_lsum(f"{sender.id}{recipient.id}")
    conv_S = calculate_ssum(f"{sender.id}{recipient.id}")
    conv_c = first_letter_index(f"{sender.id}{recipient.id}")
    conv_primary = gsp_place(conv_L, conv_S, conv_c, K=1)["primary_cell"]
    conv_cell_str = f"{conv_primary['col']},{conv_primary['row']}"

    # Create the message
    from platform.models import NSID   # we'll define NSID next
    msg = Message(
        sender_id=sender.id,
        recipient_id=recipient.id,
        body=body,
        sender_cell=sender_cell_str,
        conversation_cell=conv_cell_str,
        nsid=NSID.SOCIAL
    )
    db.add(msg)
    await db.commit()

    return {
        "message_id": str(msg.id),
        "sender_cell": sender_cell_str,
        "conversation_cell": conv_cell_str,
        "created_at": msg.created_at.isoformat()
    }


@router.get("/messages/inbox", response_model=list[MessageOut])
async def inbox(email: str = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get all messages where the user is the recipient, ordered by newest first
    messages = (await db.execute(
        select(Message)
        .where(Message.recipient_id == user.id)
        .order_by(Message.created_at.desc())
        .limit(50)
    )).scalars().all()

    return [
        {
            "id": str(m.id),
            "sender_uid": str(m.sender_id),
            "body": m.body,
            "media_url": m.media_url,
            "created_at": m.created_at.isoformat(),
            "is_edited": m.is_edited,
            "sender_cell": m.sender_cell,
            "conversation_cell": m.conversation_cell,
        }
        for m in messages
    ]


@router.delete("/messages/{message_id}")
async def delete_message(
    message_id: str,
    email: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    msg = (await db.execute(select(Message).where(Message.id == message_id))).scalar_one_or_none()
    if not msg or msg.recipient_id != user.id:
        raise HTTPException(status_code=404, detail="Message not found")

    await db.delete(msg)
    await db.commit()
    return {"status": "deleted"}

# ═══════════════════════════════════════════════════════════
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
async def main_feed(email: str = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # posts from people the user follows + own posts
    followed = select(Follow.followee_id).where(Follow.follower_id == user.id)
    query = select(Post).where(
        or_(
            Post.author_id.in_(followed),
            Post.author_id == user.id
        )
    ).order_by(Post.created_at.desc()).limit(50)
    posts = (await db.execute(query)).scalars().all()
    result = []
    for p in posts:
        author = (await db.execute(select(User).where(User.id == p.author_id))).scalar_one_or_none()
        like_count = (await db.execute(select(func.count()).where(Like.post_id == p.id))).scalar_one()
        result.append({
            "id": str(p.id),
            "content": p.content,
            "author_name": author.full_name if author else "Unknown",
            "author_id": str(p.author_id),
            "created_at": p.created_at.isoformat(),
            "likes": like_count
        })
    return result

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
# return post 
# ═══════════════════════════════════════════════════════════
@router.get("/feed")
async def friends_feed(
    email: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Return posts from users the current user follows, newest first."""
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get list of followed user IDs
    followed_ids = (await db.execute(
        select(Follow.followee_id).where(Follow.follower_id == user.id)
    )).scalars().all()

    if not followed_ids:
        return []   # user follows nobody

    posts = (await db.execute(
        select(Post).where(Post.author_id.in_(followed_ids))
        .order_by(Post.created_at.desc()).limit(50)
    )).scalars().all()

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
# lomiNews FEED (unchanged)
# ═══════════════════════════════════════════════════════════
@router.get("/news")
async def news_feed(request: Request, email: str = Depends(get_current_user), category: str = None, country: str = None, db: AsyncSession = Depends(get_db)):
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if category:
        query = select(Post).join(User, Post.author_id == User.id).where(
            User.creator_role == "newscaster", User.news_category == category
        ).order_by(Post.created_at.desc()).limit(50)
        posts = (await db.execute(query)).scalars().all()
        return [{"id": str(p.id), "content": p.content, "author_id": str(p.author_id), "created_at": p.created_at.isoformat()} for p in posts]
    followed_query = select(Follow.followee_id).where(Follow.follower_id == user.id)
    followed_newscasters = (await db.execute(select(User.id).where(User.id.in_(followed_query), User.creator_role == "newscaster"))).scalars().all()
    subscribed_categories = (await db.execute(select(NewsSubscription.category).where(NewsSubscription.user_id == user.id))).scalars().all()
    conditions = []
    if followed_newscasters:
        conditions.append(Post.author_id.in_(followed_newscasters))
    if subscribed_categories:
        conditions.append(Post.author_id.in_(select(User.id).where(User.creator_role == "newscaster", User.news_category.in_(subscribed_categories))))
    if not conditions:
        return []
    query = select(Post).where(or_(*conditions)).order_by(Post.created_at.desc()).limit(50)
    posts = (await db.execute(query)).scalars().all()
    return [{"id": str(p.id), "content": p.content, "author_id": str(p.author_id), "created_at": p.created_at.isoformat()} for p in posts]


# ═══════════════════════════════════════════════════════════
#  FEED orch)
# ═══════════════════════════════════════════════════════════

@router.get("/feed")
async def friends_feed(
    email: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Return posts from users the current user follows, ordered by recent."""
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get IDs of followed users
    followed_ids = (await db.execute(
        select(Follow.followee_id).where(Follow.follower_id == user.id)
    )).scalars().all()

    if not followed_ids:
        return []

    # Get recent posts from those users (limit 50)
    posts = (await db.execute(
        select(Post).where(Post.author_id.in_(followed_ids))
        .order_by(Post.created_at.desc()).limit(50)
    )).scalars().all()

    # For each post, also fetch the author's full name
    author_ids = [p.author_id for p in posts]
    authors = (await db.execute(
        select(User.id, User.full_name).where(User.id.in_(author_ids))
    )).all()
    author_map = {a.id: a.full_name for a in authors}

    return [
        {
            "id": str(p.id),
            "content": p.content,
            "author_name": author_map.get(p.author_id, "Unknown"),
            "author_id": str(p.author_id),
            "created_at": p.created_at.isoformat()
        }
        for p in posts
    ]