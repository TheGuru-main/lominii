from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from platform.database import get_db
from platform.auth import get_current_user

from platform.models.public import User
from platform.models.social import (
    SocialProfile,
    Follow,
)

router = APIRouter(
    prefix="/follows",
    tags=["Social Follows"],
)

# ═══════════════════════════════════════════════════════════
# FOLLOW USER
# ═══════════════════════════════════════════════════════════

@router.post("/{profile_id}")
async def follow_user(
    profile_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    me = await db.scalar(
        select(SocialProfile).where(
            SocialProfile.core_user_id == current_user.id
        )
    )

    if not me:
        raise HTTPException(404, "Social profile not found.")

    if me.id == profile_id:
        raise HTTPException(400, "You cannot follow yourself.")

    target = await db.get(SocialProfile, profile_id)

    if not target:
        raise HTTPException(404, "Profile not found.")

    existing = await db.scalar(
        select(Follow).where(
            Follow.follower_id == me.id,
            Follow.followee_id == target.id,
        )
    )

    if existing:
        return {"message": "Already following."}

    follow = Follow(
        follower_id=me.id,
        followee_id=target.id,
    )

    db.add(follow)
    await db.commit()

    return {"message": "Followed successfully."}


# ═══════════════════════════════════════════════════════════
# UNFOLLOW USER
# ═══════════════════════════════════════════════════════════

@router.delete("")
async def unfollow_user(
    request: Request,
    email: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    data = await request.json()
    target_uid = data.get("target_uid")

    if not target_uid:
        raise HTTPException(status_code=400, detail="Missing target_uid")

    follower = (
        await db.execute(
            select(User).where(User.email == email)
        )
    ).scalar_one_or_none()

    target = (
        await db.execute(
            select(User).where(User.id == target_uid)
        )
    ).scalar_one_or_none()

    if not follower or not target:
        raise HTTPException(status_code=404, detail="User not found")

    follow = (
        await db.execute(
            select(Follow).where(
                Follow.follower_id == follower.id,
                Follow.followee_id == target.id
            )
        )
    ).scalar_one_or_none()

    if not follow:
        raise HTTPException(status_code=404, detail="Not following")

    await db.delete(follow)
    await db.commit()

    return {"status": "unfollowed"}