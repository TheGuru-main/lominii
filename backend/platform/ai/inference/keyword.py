from sqlalchemy import select

from platform.models.search import SearchCache


async def keyword_inference(
    query: str,
    db,
    limit: int = 10,
):
    """
    Keyword-based inference.

    Finds searches that contain
    similar words.
    """

    query = query.lower()

    rows = (
        await db.execute(
            select(SearchCache)
        )
    ).scalars().all()

    results = []

    for row in rows:

        text = row.query.lower()

        if query == text:
            continue

        if query in text or text in query:
            results.append(text)

    return results[:limit]