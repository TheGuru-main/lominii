from sqlalchemy import select

from platform.models.ai import AIKnowledge


async def semantic_inference(
    query: str,
    db,
):
    """
    Knowledge-based inference.
    """

    rows = (
        await db.execute(
            select(AIKnowledge)
        )
    ).scalars().all()

    related = []

    query = query.lower()

    for row in rows:

        if query in row.topic.lower():

            related.append(
                row.topic
            )

    return related