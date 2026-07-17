"""
AI Related Searches Service

Builds and serves
'People also searched for'
recommendations.
"""

from sqlalchemy import select

from sqlalchemy.ext.asyncio import AsyncSession

from platform.models.ai import AIRelatedSearch


async def save_related_search(
    db: AsyncSession,
    query: str,
    related_query: str,
):
    existing = await db.execute(
        select(AIRelatedSearch).where(
            AIRelatedSearch.query == query,
            AIRelatedSearch.related_query == related_query,
        )
    )

    relation = existing.scalar_one_or_none()

    if relation:
        relation.score += 1
        await db.commit()
        await db.refresh(relation)
        return relation

    relation = AIRelatedSearch(
        query=query,
        related_query=related_query,
        score=1,
    )

    db.add(relation)
    await db.commit()
    await db.refresh(relation)

    return relation


async def get_related_searches(
    db: AsyncSession,
    query: str,
    limit: int = 10,
):
    result = await db.execute(
        select(AIRelatedSearch)
        .where(
            AIRelatedSearch.query == query
        )
        .order_by(
            AIRelatedSearch.score.desc()
        )
        .limit(limit)
    )

    return result.scalars().all()


async def increase_score(
    db: AsyncSession,
    relation: AIRelatedSearch,
):
    relation.score += 1

    await db.commit()
    await db.refresh(relation)

    return relation


async def delete_related_search(
    db: AsyncSession,
    relation: AIRelatedSearch,
):
    await db.delete(relation)
    await db.commit()