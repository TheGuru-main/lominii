from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from platform.auth import get_current_user
from platform.database import get_db
from platform.models.public import User
from platform.models.social import (
    SocialProfile,
    Post,
    Reactions,
)
from platform.nsid import NSID
from platform.schemas import (
    ReactionCreate,
    ReactionOut,
)

router = APIRouter(
    prefix="/reactions",
    tags=["Social Reactions"],
)


ALLOWED_REACTIONS = {
    "😂", "😭", "😡", "🕊️", "🙏", "😕",
    "💰", "🙌", "🪄", "💀", "🥹", "🥶",
    "❤️", "👍", "💪", "🩸", "👩‍❤️‍💋‍👩",
    "🔥", "🌠", "👏", "✌️", "🎓", "🏆",
    "🎉", "©️",
}

@router.post("/{post_id}", response_model=ReactionOut)
async def react_to_post(
    post_id: UUID,
    payload: ReactionCreate,
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

    if payload.emoji not in ALLOWED_REACTIONS:
        raise HTTPException(
            status_code=400,
            detail="Invalid reaction.",
    )

    post = await db.get(Post, post_id)

    if not post:
        raise HTTPException(
            status_code=404,
            detail="Post not found.",
        )

    reaction = await db.scalar(
        select(Reactions).where(
            Reactions.post_id == post.id,
            Reactions.user_id == profile.id,
        )
    )

    # User already reacted → update emoji

    if reaction:
        reaction.emoji = payload.emoji

        await db.commit()
        await db.refresh(reaction)

        return reaction

    # First reaction
    reaction = Reactions(
        post_id=post.id,
        user_id=profile.id,
        emoji=payload.emoji,
        nsid=NSID.SOCIAL,
    )

    db.add(reaction)

    await db.commit()
    await db.refresh(reaction)

    return reaction


@router.get("/{post_id}")
async def get_post_reactions(
    post_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    post = await db.get(Post, post_id)

    if not post:
        raise HTTPException(
            status_code=404,
            detail="Post not found.",
        )

    result = await db.execute(
        select(Reactions).where(
            Reactions.post_id == post_id
        )
    )

    return result.scalars().all()


@router.delete("/{post_id}")
async def remove_reaction(
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

    reaction = await db.scalar(
        select(Reactions).where(
            Reactions.post_id == post_id,
            Reactions.user_id == profile.id,
        )
    )

    if not reaction:
        raise HTTPException(
            status_code=404,
            detail="Reaction not found.",
        )

    await db.delete(reaction)
    await db.commit()

    return {
        "message": "Removed reaction."
    }