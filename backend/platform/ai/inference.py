"""
AI Inference Engine

Discovers semantic relationships between searches.
"""

from collections import Counter


def infer_related_queries(
    query: str,
    search_history: list[str],
    limit: int = 10,
) -> list[str]:
    """
    Very first inference engine.

    Later this will be replaced by embeddings,
    vector search and LLM reasoning.
    """

    query = query.lower()

    related = []

    for item in search_history:
        text = item.lower()

        if query == text:
            continue

        if query in text or text in query:
            related.append(item)

    counts = Counter(related)

    ranked = sorted(
        counts.items(),
        key=lambda x: x[1],
        reverse=True,
    )

    return [
        word
        for word, _
        in ranked[:limit]
    ]