"""
AI Memory Service

Handles conversations, messages,
long-term memory, knowledge,
and related searches.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from platform.models.ai import (
    AIConversation,
    AIMessage,
    AIMemory,
    AIKnowledge,
    AIRelatedSearch,
)


# ==========================================================
# CONVERSATIONS
# ==========================================================

async def create_conversation(
    db: AsyncSession,
    user_id: UUID,
    workspace: str = "search",
    title: str | None = None,
):
    conversation = AIConversation(
        user_id=user_id,
        workspace=workspace,
        title=title,
    )

    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)

    return conversation


async def get_conversation(
    db: AsyncSession,
    conversation_id: UUID,
):
    return await db.get(
        AIConversation,
        conversation_id,
    )


# ==========================================================
# MESSAGES
# ==========================================================

async def save_message(
    db: AsyncSession,
    conversation_id: UUID,
    role: str,
    content: str,
):
    message = AIMessage(
        conversation_id=conversation_id,
        role=role,
        content=content,
    )

    db.add(message)
    await db.commit()

    return message


async def get_messages(
    db: AsyncSession,
    conversation_id: UUID,
):
    result = await db.execute(
        select(AIMessage)
        .where(
            AIMessage.conversation_id == conversation_id
        )
        .order_by(
            AIMessage.created_at.asc()
        )
    )

    return result.scalars().all()


# ==========================================================
# LONG TERM MEMORY
# ==========================================================

async def remember(
    db: AsyncSession,
    user_id: UUID,
    memory_type: str,
    content: str,
    title: str | None = None,
):
    memory = AIMemory(
        user_id=user_id,
        memory_type=memory_type,
        title=title,
        content=content,
    )

    db.add(memory)
    await db.commit()

    return memory


async def load_memory(
    db: AsyncSession,
    user_id: UUID,
):
    result = await db.execute(
        select(AIMemory)
        .where(
            AIMemory.user_id == user_id
        )
    )

    return result.scalars().all()


# ==========================================================
# KNOWLEDGE
# ==========================================================

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

    return knowledge


# ==========================================================
# RELATED SEARCHES
# ==========================================================

async def save_related_search(
    db: AsyncSession,
    query: str,
    related_query: str,
):
    relation = AIRelatedSearch(
        query=query,
        related_query=related_query,
    )

    db.add(relation)
    await db.commit()

    return relation


async def get_related_searches(
    db: AsyncSession,
    query: str,
):
    result = await db.execute(
        select(AIRelatedSearch)
        .where(
            AIRelatedSearch.query == query
        )
        .order_by(
            AIRelatedSearch.score.desc()
        )
    )

    return result.scalars().all()