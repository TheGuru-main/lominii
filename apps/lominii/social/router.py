"""LOMINII Social Room – Router (and lomiNews acess)"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from platform.database import get_db
from platform.auth import get_current_user
from platform.content_filter import is_blocked
from platform.gsp import calculate_lsum, calculate_ssum, first_letter_index, gsp_place
from platform.models import User, Message, Follow, Post, Comment

router = APIRouter(prefix="/api/social", tags=["Social"])

# ═══════════════════════════════════════════════════════════
# MESSAGING (unchanged)
# ═══════════════════════════════════════════════════════════

@router.post("/messages/send")
async def send_message(request: Request, email: str = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    data = await request.json()
    target_uid = data.get("target_uid")
    text = data.get("text", "").strip()
    if not target_uid or not text:
        raise HTTPException(status_code=400, detail="Missing target_uid or text")
    if is_blocked(text):
        raise HTTPException(status_code=400, detail="Blocked content")

    sender = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    receiver = (await db.execute(select(User).where(User.id == target_uid))).scalar_one_or_none()
    if not sender or not receiver:
        raise HTTPException(status_code=404, detail="User not found")

    L = calculate_lsum(receiver.full_name)
    S = calculate_ssum(receiver.full_name)
    c = first_letter_index(receiver.full_name)
    primary = gsp_place(L, S, c, K=1)["primary_cell"]

    msg = Message(from_user_id=sender.id, to_user_id=receiver.id, text=text,
                  gsp_cell=f"{primary['col']},{primary['row']}")
    db.add(msg)
    await db.commit()
    return {"message_id": str(msg.id), "gsp_cell": f"{primary['col']},{primary['row']}",
            "timestamp": msg.created_at.isoformat()}

@router.get("/messages/inbox")
async def inbox(email: str = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    messages = (await db.execute(
        select(Message).where(Message.to_user_id == user.id).order_by(Message.created_at.desc()).limit(50)
    )).scalars().all()
    return [{"id": str(m.id), "from_uid": str(m.from_user_id), "text": m.text,
             "timestamp": m.created_at.isoformat()} for m in messages]

@router.delete("/messages/{message_id}")
async def delete_message(message_id: str, email: str = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    msg = (await db.execute(select(Message).where(Message.id == message_id))).scalar_one_or_none()
    if not msg or msg.to_user_id != user.id:
        raise HTTPException(status_code=404, detail="Message not found")
    await db.delete(msg)
    await db.commit()
    return {"status": "deleted"}

# ═══════════════════════════════════════════════════════════
# FOLLOWS (unchanged)
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
# POSTS & COMMENTS (unchanged)
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

# ═══════════════════════════════════════════════════════════
# lomiNews FEED (NEW)
# ═══════════════════════════════════════════════════════════

@router.get("/news")
async def news_feed(category: str = None, country: str = None, db: AsyncSession = Depends(get_db)):
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