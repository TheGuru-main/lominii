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

@router.delete("/{profile_id}")
async def unfollow_user(
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

    follow = await db.scalar(
        select(Follow).where(
            Follow.follower_id == me.id,
            Follow.followee_id == profile_id,
        )
    )

    if not follow:
        raise HTTPException(404, "Follow relationship not found.")

    await db.delete(follow)
    await db.commit()

    return {"message": "Unfollowed successfully."}