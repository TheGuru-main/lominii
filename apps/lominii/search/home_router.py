"""LOMINII home cards backed by stored search and news data."""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from lominii_platform.database import get_db
from lominii_platform.models.search import Search, Trending, NewsArticle, NewsCache

router = APIRouter(tags=["Home"])


@router.get("/api/trending")
async def get_trending(db: AsyncSession = Depends(get_db)):
    """Return saved trending terms, falling back to search-history counts."""
    try:
        rows = (
            await db.execute(
                select(Trending.query)
                .where(Trending.query.is_not(None))
                .order_by(Trending.count.desc(), Trending.updated_at.desc())
                .limit(10)
            )
        ).scalars().all()

        if rows:
            return list(dict.fromkeys(
                str(item) for item in rows if str(item).strip()
            ))

        derived = (
            await db.execute(
                select(Search.query, func.count(Search.id).label("hits"))
                .where(Search.query.is_not(None))
                .group_by(Search.query)
                .order_by(func.count(Search.id).desc())
                .limit(10)
            )
        ).all()

        return [str(row[0]) for row in derived if row[0]]

    except Exception as exc:
        await db.rollback()
        print(f"Trending endpoint unavailable: {exc}")
        return []


@router.get("/api/news")
async def get_news(
    category: str = "general",
    db: AsyncSession = Depends(get_db)
):
    """Return cached or stored articles without fabricating headlines."""
    requested = (category or "general").strip().lower()[:50]

    try:
        cached = (
            await db.execute(
                select(NewsCache)
                .where(NewsCache.category == requested)
                .limit(1)
            )
        ).scalar_one_or_none()

        if cached and isinstance(cached.articles, list):
            return {
                "category": requested,
                "articles": cached.articles[:10]
            }

        query = select(NewsArticle).order_by(
            NewsArticle.published_at.desc()
        )

        if requested != "general":
            query = query.where(NewsArticle.category == requested)

        rows = (await db.execute(query.limit(10))).scalars().all()

        articles = [
            {
                "title": row.title,
                "url": row.url,
                "source": row.source,
                "published_at": (
                    row.published_at.isoformat()
                    if row.published_at else None
                )
            }
            for row in rows
            if row.title and row.url
        ]

        return {"category": requested, "articles": articles}

    except Exception as exc:
        await db.rollback()
        print(f"News endpoint unavailable: {exc}")
        return {"category": requested, "articles": []}
