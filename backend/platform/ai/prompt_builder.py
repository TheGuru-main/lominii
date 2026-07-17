"""
AI Prompt Builder

Builds the final prompt sent to the AI provider.

Pipeline

Intent Analyzer
        ↓
Prompt Builder
        ↓
Gateway
        ↓
Provider
"""

from platform.prompts import (
    PROMPTS,
    detect_domain,
    get_prompt,
)


def build_prompt(
    *,
    query: str,
    sources: str = "",
    country: str = "Nigeria",
    language: str = "en",
    tier: str = "free",
    workspace: str = "search",
    conversation_history: str = "",
    intent: str | None = None,
) -> str:
    """
    Build the final AI prompt.
    """

    # --------------------------------------------------
    # Conversation Workspace
    # --------------------------------------------------

    if workspace == "conversation":
        return PROMPTS["conversation"].format(
            query=query,
            sources=sources,
            country=country,
            language=language,
            conversation_history=conversation_history,
        )

    # --------------------------------------------------
    # Search Workspace
    # Expert-first architecture
    # --------------------------------------------------

    if workspace == "search":
        template = get_prompt(tier)

        return template.format(
            query=query,
            sources=sources,
            country=country,
            language=language,
        )

    # --------------------------------------------------
    # Domain Prompt
    # --------------------------------------------------

    domain = detect_domain(query)

    template = PROMPTS.get(
        domain,
        PROMPTS["general"],
    )

    return template.format(
        query=query,
        sources=sources,
        country=country,
        language=language,
    )