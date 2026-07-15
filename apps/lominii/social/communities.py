from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from uuid import UUID

from platform.database import get_db
from platform.auth import get_current_user

from platform.models.public import User
from platform.models.social import (
    SocialProfile,
    Community,
    CommunityMember,
)

router = APIRouter(
    prefix="/communities",
    tags=["Social Communities"],
)


@router.post("/")
async def create_community(
    data: dict,
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

    community = Community(
        name=data["name"],
        description=data.get("description"),
        created_by=profile.id,
        visibility=data.get("visibility", "public"),
        max_members=data.get("max_members", 1000),
    )

    db.add(community)
    await db.flush()

    owner = CommunityMember(
        community_id=community.id,
        user_id=profile.id,
        role="owner",
    )

    db.add(owner)

    await db.commit()
    await db.refresh(community)

    return {
        "community_id": str(community.id),
        "name": community.name,
        "visibility": community.visibility,
        "max_members": community.max_members,
    }


@router.post("/{community_id}/join")
async def join_community(
    community_id: UUID,
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

    community = await db.get(Community, community_id)

    if not community:
        raise HTTPException(
            status_code=404,
            detail="Community not found",
        )

    if community.visibility == "private":
        raise HTTPException(
            status_code=403,
            detail="This community is private. You must be invited.",
        )

    existing = await db.scalar(
        select(CommunityMember).where(
            CommunityMember.community_id == community_id,
            CommunityMember.user_id == profile.id,
        )
    )

    if existing:
        raise HTTPException(
            status_code=400,
            detail="You are already a member.",
        )

    member_count = await db.execute(
        select(CommunityMember).where(
            CommunityMember.community_id == community_id
        )
    )

    if len(member_count.scalars().all()) >= community.max_members:
        raise HTTPException(
            status_code=400,
            detail="Community has reached its member limit.",
        )

    member = CommunityMember(
        community_id=community.id,
        user_id=profile.id,
        role="member",
    )

    db.add(member)
    await db.commit()

    return {
        "message": "Joined community successfully."
    }