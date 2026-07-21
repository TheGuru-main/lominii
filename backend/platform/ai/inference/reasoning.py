from platform.ai.gateway import generate


async def reasoning_inference(
    query: str,
):
    """
    AI reasoning.

    Future:
    Return structured related searches.
    """

    prompt = f"""
Suggest five search queries related to:

{query}

Return only the queries.
"""

    response = await generate(prompt)

    return [
        line.strip()
        for line in response.splitlines()
        if line.strip()
    ]