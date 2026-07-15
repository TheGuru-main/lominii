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
    CommunityPost
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


@router.delete("/{community_id}/leave")
async def leave_community(
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

    membership = await db.scalar(
        select(CommunityMember).where(
            CommunityMember.community_id == community_id,
            CommunityMember.user_id == profile.id,
        )
    )

    if not membership:
        raise HTTPException(
            status_code=404,
            detail="You are not a member of this community.",
        )

    if membership.role == "owner":
        raise HTTPException(
            status_code=400,
            detail="The owner cannot leave the community. Delete it or transfer ownership first.",
        )

    await db.delete(membership)
    await db.commit()

    return {
        "message": "Successfully left. You are no longer a member of the community."
    }


@router.post("/{community_id}/invite/{profile_id}")
async def invite_member(
    community_id: UUID,
    profile_id: UUID,
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

    inviter = await db.scalar(
        select(CommunityMember).where(
            CommunityMember.community_id == community_id,
            CommunityMember.user_id == profile.id,
        )
    )

    if not inviter:
        raise HTTPException(
            status_code=403,
            detail="You are not a community member.",
        )

    if inviter.role not in ("owner", "admin", "moderator"):
        raise HTTPException(
            status_code=403,
            detail="Only owners, admins or moderators can invite members.",
        )

    existing = await db.scalar(
        select(CommunityMember).where(
            CommunityMember.community_id == community_id,
            CommunityMember.user_id == profile_id,
        )
    )

    if existing:
        raise HTTPException(
            status_code=400,
            detail="User is already a member.",
        )

    member = CommunityMember(
        community_id=community_id,
        user_id=profile_id,
        role="member",
    )

    db.add(member)
    await db.commit()

    return {
        "message": "Member added successfully."
    }


@router.patch("/{community_id}/settings")
async def update_community_settings(
    community_id: UUID,
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

    membership = await db.scalar(
        select(CommunityMember).where(
            CommunityMember.community_id == community_id,
            CommunityMember.user_id == profile.id,
        )
    )

    if not membership:
        raise HTTPException(
            status_code=403,
            detail="You are not a member of this community.",
        )

    if membership.role not in ("owner", "admin"):
        raise HTTPException(
            status_code=403,
            detail="Only owners and admins can update settings.",
        )

    community = await db.get(
        Community,
        community_id,
    )

    if not community:
        raise HTTPException(
            status_code=404,
            detail="Community not found.",
        )

    if "name" in data:
        community.name = data["name"]

    if "description" in data:
        community.description = data["description"]

    if "visibility" in data:
        community.visibility = data["visibility"]

    if "max_members" in data:
        community.max_members = data["max_members"]

    await db.commit()
    await db.refresh(community)

    return {
        "message": "Community settings updated successfully.",
        "community": {
            "id": str(community.id),
            "name": community.name,
            "visibility": community.visibility,
            "max_members": community.max_members,
        },
    }


@router.patch("/{community_id}/members/{member_id}/role")
async def update_member_role(
    community_id: UUID,
    member_id: UUID,
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
            detail="Social profile not found.",
        )

    actor = await db.scalar(
        select(CommunityMember).where(
            CommunityMember.community_id == community_id,
            CommunityMember.user_id == profile.id,
        )
    )

    if not actor or actor.role != "owner":
        raise HTTPException(
            status_code=403,
            detail="Only the community owner can change member roles.",
        )

    member = await db.scalar(
        select(CommunityMember).where(
            CommunityMember.community_id == community_id,
            CommunityMember.user_id == member_id,
        )
    )

    if not member:
        raise HTTPException(
            status_code=404,
            detail="Member not found.",
        )

    new_role = data.get("role")

    if new_role not in (
        "member",
        "moderator",
        "admin",
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid role.",
        )

    member.role = new_role

    await db.commit()

    return {
        "message": f"Role updated to {new_role}.",
    }


@router.delete("/{community_id}/members/{member_id}")
async def remove_member(
    community_id: UUID,
    member_id: UUID,
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
            detail="Social profile not found.",
        )

    actor = await db.scalar(
        select(CommunityMember).where(
            CommunityMember.community_id == community_id,
            CommunityMember.user_id == profile.id,
        )
    )

    if not actor:
        raise HTTPException(
            status_code=403,
            detail="You are not a community member.",
        )

    if actor.role not in (
        "owner",
        "admin",
        "moderator",
    ):
        raise HTTPException(
            status_code=403,
            detail="Permission denied.",
        )

    member = await db.scalar(
        select(CommunityMember).where(
            CommunityMember.community_id == community_id,
            CommunityMember.user_id == member_id,
        )
    )

    if not member:
        raise HTTPException(
            status_code=404,
            detail="Member not found.",
        )

    if member.role == "owner":
        raise HTTPException(
            status_code=400,
            detail="Community owner cannot be removed.",
        )

    if actor.role == "moderator" and member.role != "member":
        raise HTTPException(
            status_code=403,
            detail="Moderators can only remove members.",
        )

    if actor.role == "admin" and member.role == "admin":
        raise HTTPException(
            status_code=403,
            detail="Admins cannot remove other admins.",
        )

    await db.delete(member)
    await db.commit()

    return {
        "message": "Member removed successfully."
    }


@router.patch("/{community_id}/transfer/{member_id}")
async def transfer_ownership(
    community_id: UUID,
    member_id: UUID,
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
            detail="Social profile not found.",
        )

    owner = await db.scalar(
        select(CommunityMember).where(
            CommunityMember.community_id == community_id,
            CommunityMember.user_id == profile.id,
        )
    )

    if not owner or owner.role != "owner":
        raise HTTPException(
            status_code=403,
            detail="Only the owner can transfer ownership.",
        )

    new_owner = await db.scalar(
        select(CommunityMember).where(
            CommunityMember.community_id == community_id,
            CommunityMember.user_id == member_id,
        )
    )

    if not new_owner:
        raise HTTPException(
            status_code=404,
            detail="Selected member not found.",
        )

    owner.role = "admin"
    new_owner.role = "owner"

    await db.commit()

    return {
        "message": "Community ownership transferred successfully."
    }


@router.get("/{community_id}/members")
async def get_community_members(
    community_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    community = await db.get(
        Community,
        community_id,
    )

    if not community:
        raise HTTPException(
            status_code=404,
            detail="Community not found.",
        )

    result = await db.execute(
        select(
            CommunityMember,
            SocialProfile,
        )
        .join(
            SocialProfile,
            CommunityMember.user_id == SocialProfile.id,
        )
        .where(
            CommunityMember.community_id == community_id,
        )
        .order_by(
            CommunityMember.joined_at.asc(),
        )
    )

    members = result.all()

    return [
        {
            "profile_id": str(profile.id),
            "social_uid": profile.social_uid,
            "full_name": profile.full_name,
            "avatar_url": profile.avatar_url,
            "role": member.role,
            "joined_at": member.joined_at,
        }
        for member, profile in members
    ]

@router.delete("/{community_id}")
async def delete_community(
    community_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = await db.scalar(
        select(SocialProfile).where(
            SocialProfile.core_user_id == current_user.id,
        )
    )

    if not profile:
        raise HTTPException(
            status_code=404,
            detail="Social profile not found.",
        )

    owner = await db.scalar(
        select(CommunityMember).where(
            CommunityMember.community_id == community_id,
            CommunityMember.user_id == profile.id,
        )
    )

    if not owner or owner.role != "owner":
        raise HTTPException(
            status_code=403,
            detail="Only the community owner can delete the community.",
        )

    community = await db.get(
        Community,
        community_id,
    )

    if not community:
        raise HTTPException(
            status_code=404,
            detail="Community not found.",
        )

    await db.delete(community)
    await db.commit()

    return {
        "message": "Community deleted successfully."
    }


@router.post("/{community_id}/posts")
async def create_community_post(
    community_id: UUID,
    content: str,
    media_urls: list[str] | None = None,
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
            detail="Social profile not found.",
        )

    member = await db.scalar(
        select(CommunityMember).where(
            CommunityMember.community_id == community_id,
            CommunityMember.user_id == profile.id,
        )
    )

    if not member:
        raise HTTPException(
            status_code=403,
            detail="You are not a member of this community.",
        )

    post = CommunityPost(
        community_id=community_id,
        author_id=profile.id,
        content=content,
        media_urls=media_urls or [],
        nsid=NSID.SOCIAL,
    )

    db.add(post)
    await db.commit()
    await db.refresh(post)

    return post


@router.get("/{community_id}/posts")
async def get_community_posts(
    community_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    community = await db.get(
        Community,
        community_id,
    )

    if not community:
        raise HTTPException(
            status_code=404,
            detail="Community not found.",
        )

    result = await db.execute(
        select(CommunityPost)
        .where(
            CommunityPost.community_id == community_id,
            CommunityPost.deleted_at == None,
        )
        .order_by(
            CommunityPost.created_at.desc(),
        )
    )

    posts = result.scalars().all()

    return posts


@router.put("/posts/{post_id}")
async def edit_community_post(
    post_id: UUID,
    content: str,
    media_urls: list[str] | None = None,
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
            detail="Social profile not found.",
        )

    post = await db.get(
        CommunityPost,
        post_id,
    )

    if not post or post.deleted_at is not None:
        raise HTTPException(
            status_code=404,
            detail="Community post not found.",
        )

    if post.author_id != profile.id:
        raise HTTPException(
            status_code=403,
            detail="You can only edit your own posts.",
        )

    post.content = content

    if media_urls is not None:
        post.media_urls = media_urls

    post.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(post)

    return post


@router.delete("/posts/{post_id}")
async def delete_community_post(
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
            detail="Social profile not found.",
        )

    post = await db.get(
        CommunityPost,
        post_id,
    )

    if not post or post.deleted_at is not None:
        raise HTTPException(
            status_code=404,
            detail="Community post not found.",
        )

    if post.author_id != profile.id:
        raise HTTPException(
            status_code=403,
            detail="You can only delete your own posts.",
        )

    post.deleted_at = datetime.utcnow()

    await db.commit()

    return {
        "message": "Community post deleted successfully."
    }


@router.patch("/posts/{post_id}/pin")
async def pin_community_post(
    post_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = await db.scalar(
        select(SocialProfile).where(
            SocialProfile.core_user_id == current_user.id
        )
    )

    post = await db.get(CommunityPost, post_id)

    if not post:
        raise HTTPException(404, "Post not found.")

    member = await db.scalar(
        select(CommunityMember).where(
            CommunityMember.community_id == post.community_id,
            CommunityMember.user_id == profile.id,
        )
    )

    if not member or member.role not in [
        "owner",
        "admin",
        "moderator",
    ]:
        raise HTTPException(
            403,
            "Only community admins can pin posts.",
        )

    post.is_pinned = True

    await db.commit()
    await db.refresh(post)

    return post


@router.patch("/posts/{post_id}/unpin")
async def unpin_community_post(
    post_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = await db.scalar(
        select(SocialProfile).where(
            SocialProfile.core_user_id == current_user.id
        )
    )

    post = await db.get(CommunityPost, post_id)

    if not post:
        raise HTTPException(404, "Post not found.")

    member = await db.scalar(
        select(CommunityMember).where(
            CommunityMember.community_id == post.community_id,
            CommunityMember.user_id == profile.id,
        )
    )

    if not member or member.role not in [
        "owner",
        "admin",
        "moderator",
    ]:
        raise HTTPException(
            403,
            "Only community admins can unpin posts.",
        )

    post.is_pinned = False

    await db.commit()
    await db.refresh(post)

    return post


@router.post("/{community_id}/announcement")
async def create_announcement(
    community_id: UUID,
    content: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = await db.scalar(
        select(SocialProfile).where(
            SocialProfile.core_user_id == current_user.id
        )
    )

    member = await db.scalar(
        select(CommunityMember).where(
            CommunityMember.community_id == community_id,
            CommunityMember.user_id == profile.id,
        )
    )

    if not member or member.role not in (
        "owner",
        "admin",
        "moderator",
    ):
        raise HTTPException(
            status_code=403,
            detail="Only moderators can create announcements.",
        )

    announcement = CommunityPost(
        community_id=community_id,
        author_id=profile.id,
        content=content,
        media_urls=[],
        is_announcement=True,
        nsid=NSID.SOCIAL,
    )

    db.add(announcement)
    await db.commit()
    await db.refresh(announcement)

    return announcement


@router.patch("/{community_id}/members/{member_id}/promote")
async def promote_member(
    community_id: UUID,
    member_id: UUID,
    role: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
       ...

@router.patch("/{community_id}/members/{member_id}/demote")
async def demote_member(...)


@router.delete("/{community_id}/members/{member_id}")
async def remove_member(...)