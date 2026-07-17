"""
AI Knowledge Service

Stores reusable AI knowledge extracted
from trusted searches and future sources.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from platform.models.ai import AIKnowledge


async def save_knowledge(
    db: AsyncSession,
    topic: str,
    summary: str,
    source: str | None = None,
):
    knowledge = AIKnowledge(
        topic=topic,
        summary=summary,
        source=source,
    )

    db.add(knowledge)
    await db.commit()
    await db.refresh(knowledge)

    return knowledge


async def get_knowledge(
    db: AsyncSession,
    topic: str,
):
    result = await db.execute(
        select(AIKnowledge).where(
            AIKnowledge.topic == topic
        )
    )

    return result.scalar_one_or_none()


async def search_knowledge(
    db: AsyncSession,
    keyword: str,
):
    result = await db.execute(
        select(AIKnowledge).where(
            AIKnowledge.topic.ilike(f"%{keyword}%")
        )
    )

    return result.scalars().all()


async def update_knowledge(
    db: AsyncSession,
    knowledge: AIKnowledge,
    summary: str,
):
    knowledge.summary = summary

    await db.commit()
    await db.refresh(knowledge)

    return knowledge


async def delete_knowledge(
    db: AsyncSession,
    knowledge: AIKnowledge,
):
    await db.delete(knowledge)
    await db.commit()