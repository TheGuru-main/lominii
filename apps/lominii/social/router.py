"""
LOMINII Social Room – Router
Messaging, Follows, Posts, Comments — all driven by core UID.
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from platform.database import get_db
from platform.auth import get_current_user
from platform.content_filter import is_blocked
from platform.gsp import calculate_lsum, calculate_ssum, first_letter_index, gsp_place

router = APIRouter(prefix="/api/social", tags=["Social"])

# ═══════════════════════════════════════════════════════════
# MESSAGING
# ═══════════════════════════════════════════════════════════

@router.post("/messages/send")
async def send_message(
    request: Request,
    email: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    data = await request.json()
    target_uid = data.get("target_uid")
    text = data.get("text", "").strip()

    if not target_uid or not text:
        raise HTTPException(status_code=400, detail="Missing target_uid or text")
    if is_blocked(text):
        raise HTTPException(status_code=400, detail="Blocked content")

    # Get sender and receiver from database
    from models import User  # We'll create models.py soon; for now, assume it exists
    sender = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if not sender:
        raise HTTPException(status_code=404, detail="Sender not found")

    receiver = (await db.execute(select(User).where(User.id == target_uid))).scalar_one_or_none()
    if not receiver:
        raise HTTPException(status_code=404, detail="Receiver not found")

    # Compute receiver's point-node cell (for future Wizard DB)
    L = calculate_lsum(receiver.full_name)
    S = calculate_ssum(receiver.full_name)
    c = first_letter_index(receiver.full_name)
    primary = gsp_place(L, S, c, K=1)["primary_cell"]

    # Store message in database (search.messages table, reusing general messaging)
    from models import Message  # We'll add Message model
    msg = Message(
        from_user_id=sender.id,
        to_user_id=receiver.id,
        text=text,
        gsp_cell=f"{primary['col']},{primary['row']}"
    )
    db.add(msg)
    await db.commit()

    return {
        "message_id": str(msg.id),
        "gsp_cell": f"{primary['col']},{primary['row']}",
        "timestamp": msg.created_at.isoformat()
    }


@router.get("/messages/inbox")
async def inbox(
    email: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    from models import User, Message
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    messages = (await db.execute(
        select(Message).where(Message.to_user_id == user.id).order_by(Message.created_at.desc()).limit(50)
    )).scalars().all()

    return [
        {
            "id": str(m.id),
            "from_uid": str(m.from_user_id),
            "text": m.text,
            "timestamp": m.created_at.isoformat()
        }
        for m in messages
    ]


@router.delete("/messages/{message_id}")
async def delete_message(
    message_id: str,
    email: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    from models import User, Message
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
# FOLLOWS
# ═══════════════════════════════════════════════════════════

@router.post("/follow")
async def follow_user(
    request: Request,
    email: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    data = await request.json()
    target_uid = data.get("target_uid")
    if not target_uid:
        raise HTTPException(status_code=400, detail="Missing target_uid")

    from models import User, Follow
    follower = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    target = (await db.execute(select(User).where(User.id == target_uid))).scalar_one_or_none()
    if not follower or not target:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if already following
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
async def unfollow_user(
    request: Request,
    email: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    data = await request.json()
    target_uid = data.get("target_uid")
    if not target_uid:
        raise HTTPException(status_code=400, detail="Missing target_uid")

    from models import User, Follow
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
# POSTS & COMMENTS
# ═══════════════════════════════════════════════════════════

@router.post("/post")
async def create_post(
    request: Request,
    email: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    data = await request.json()
    content = data.get("content", "").strip()
    if not content or is_blocked(content):
        raise HTTPException(status_code=400, detail="Invalid or blocked content")

    from models import User, Post
    author = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if not author:
        raise HTTPException(status_code=404, detail="User not found")

    post = Post(author_id=author.id, content=content)
    db.add(post)
    await db.commit()
    return {"post_id": str(post.id), "created_at": post.created_at.isoformat()}


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

    from models import User, Post, Comment
    author = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    post = (await db.execute(select(Post).where(Post.id == post_id))).scalar_one_or_none()
    if not author or not post:
        raise HTTPException(status_code=404, detail="Not found")

    comment = Comment(post_id=post.id, author_id=author.id, content=content)
    db.add(comment)
    await db.commit()
    return {"comment_id": str(comment.id), "created_at": comment.created_at.isoformat()}