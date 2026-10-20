"""LOMINII persistent in-app notification service."""

from sqlalchemy import select

from lominii_platform.database import async_session
from lominii_platform.models.news import NewsNotification, NewsSubscription


SPORTS_CATEGORIES = {
    "sports",
    "football",
    "live_football",
    "all",
}


async def send_notification(user_id, title, body, data=None):
    """Persist an in-app notification for one user."""
    data = data or {}

    notification = NewsNotification(
        user_id=user_id,
        title=str(title)[:255],
        body=str(body),
        article_url=data.get("url", "/sports"),
    )

    async with async_session() as db:
        db.add(notification)
        await db.commit()
        await db.refresh(notification)

    return notification.id


async def broadcast_notification(title, body, data=None):
    """Persist a notification for enabled sports subscribers."""
    data = data or {}

    async with async_session() as db:
        result = await db.execute(
            select(NewsSubscription.user_id, NewsSubscription.category)
            .where(NewsSubscription.enabled.is_(True))
        )

        user_ids = {
            user_id
            for user_id, category in result.all()
            if category and category.strip().lower() in SPORTS_CATEGORIES
        }

        for user_id in user_ids:
            db.add(
                NewsNotification(
                    user_id=user_id,
                    title=str(title)[:255],
                    body=str(body),
                    article_url=data.get("url", "/sports"),
                )
            )

        if user_ids:
            await db.commit()

    return len(user_ids)
