"""
AI Gateway

Single entry point for every AI request in LOMINII.
"""

from platform.ai.providers import generate as provider_generate


async def generate(
    prompt: str,
    *,
    intent: str | None = None,
    workspace: str | None = None,
    user_id: str | None = None,
) -> str:
    """
    Central AI gateway.

    Future responsibilities:
    - Provider routing
    - Prompt optimization
    - Memory injection
    - Intent-aware model selection
    - Caching
    - Logging
    - Cost tracking
    - AI moderation
    """

    response = await provider_generate(prompt)

    return response