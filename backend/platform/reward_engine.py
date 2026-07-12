"""
LOMINII Reward Engine

Shared reward service for every workspace and game.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from platform.models import GameReward, GameAchievement


async def grant_reward(
    db: AsyncSession,
    user_id,
    game_id: str,
    reward_type: str,
    amount: int = 0,
    description: str = ""
):
    reward = GameReward(
        user_id=user_id,
        game_id=game_id,
        reward_type=reward_type,
        amount=amount,
        description=description
    )

    db.add(reward)
    await db.commit()
    await db.refresh(reward)

    return reward


async def unlock_achievement(
    db: AsyncSession,
    user_id,
    game_id: str,
    achievement_key: str
):
    existing = (
        await db.execute(
            select(GameAchievement).where(
                GameAchievement.user_id == user_id,
                GameAchievement.game_id == game_id,
                GameAchievement.achievement_key == achievement_key
            )
        )
    ).scalar_one_or_none()

    if existing:
        return existing

    achievement = GameAchievement(
        user_id=user_id,
        game_id=game_id,
        achievement_key=achievement_key
    )

    db.add(achievement)
    await db.commit()
    await db.refresh(achievement)

    return achievement


async def get_rewards(
    db: AsyncSession,
    user_id
):
    result = await db.execute(
        select(GameReward).where(
            GameReward.user_id == user_id
        )
    )

    return result.scalars().all()


async def get_achievements(
    db: AsyncSession,
    user_id
):
    result = await db.execute(
        select(GameAchievement).where(
            GameAchievement.user_id == user_id
        )
    )

    return result.scalars().all()