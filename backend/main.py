"""
LOMINII — Main FastAPI Application.
Shared platform with independent application modules.
"""

import asyncio

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from sqlalchemy import text
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from apps.lominii.admin.router import router as admin_router
from apps.lominii.auth.router import router as auth_router
from apps.lominii.chat.router import router as chat_router
from apps.lominii.football.router import router as football_router
from apps.lominii.games.router import router as games_router
from apps.lominii.search.router import router as search_router
from apps.lominii.search.home_router import router as home_router
from apps.lominii.media.router import router as scrapingbee_router

from lominii_platform.database import Base, engine
from lominii_platform.game_engine import active_sessions
from lominii_platform.sportmonk_service import start_webhook_proxy_loop


app = FastAPI(
    title="LOMINII Platform",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(search_router)
app.include_router(home_router)
app.include_router(scrapingbee_router)
app.include_router(games_router)
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(football_router)
app.include_router(chat_router)


@app.on_event("startup")
async def startup():
    """Initialize database tables and start the live-score proxy."""
    async with engine.begin() as connection:
        await connection.execute(text("CREATE SCHEMA IF NOT EXISTS news"))
        await connection.execute(text("CREATE SCHEMA IF NOT EXISTS search"))
        await connection.execute(text("CREATE SCHEMA IF NOT EXISTS game"))
        await connection.execute(text("CREATE SCHEMA IF NOT EXISTS messaging"))
        await connection.execute(text("CREATE SCHEMA IF NOT EXISTS crawler"))

        # Idempotent compatibility migration for existing user tables.
        # create_all() creates missing tables but does not add missing columns.
        await connection.execute(text("CREATE TABLE IF NOT EXISTS public.users ("
            "id UUID PRIMARY KEY, email VARCHAR(255) UNIQUE NOT NULL, "
            "full_name VARCHAR(255) NOT NULL, password_hash VARCHAR(255) NOT NULL)"))

        user_column_migrations = [
            "ALTER TABLE public.users ADD COLUMN IF NOT EXISTS google_id VARCHAR(255)",
            "ALTER TABLE public.users ADD COLUMN IF NOT EXISTS phone VARCHAR(20)",
            "ALTER TABLE public.users ADD COLUMN IF NOT EXISTS country VARCHAR(100)",
            "ALTER TABLE public.users ADD COLUMN IF NOT EXISTS state VARCHAR(100)",
            "ALTER TABLE public.users ADD COLUMN IF NOT EXISTS lga VARCHAR(100)",
            "ALTER TABLE public.users ADD COLUMN IF NOT EXISTS city VARCHAR(100)",
            "ALTER TABLE public.users ADD COLUMN IF NOT EXISTS primary_community_1 VARCHAR(150)",
            "ALTER TABLE public.users ADD COLUMN IF NOT EXISTS primary_community_2 VARCHAR(150)",
            "ALTER TABLE public.users ADD COLUMN IF NOT EXISTS profile_picture_url VARCHAR(500)",
            "ALTER TABLE public.users ADD COLUMN IF NOT EXISTS additional_image_url VARCHAR(500)",
            "ALTER TABLE public.users ADD COLUMN IF NOT EXISTS lomimail_address VARCHAR(255)",
            "ALTER TABLE public.users ADD COLUMN IF NOT EXISTS lomimail_uid VARCHAR(20)",
            "ALTER TABLE public.users ADD COLUMN IF NOT EXISTS phone_verified BOOLEAN NOT NULL DEFAULT FALSE",
            "ALTER TABLE public.users ADD COLUMN IF NOT EXISTS lomimail_handshake_at TIMESTAMP WITHOUT TIME ZONE",
            "ALTER TABLE public.users ADD COLUMN IF NOT EXISTS lomimail_startrow SMALLINT",
            "ALTER TABLE public.users ADD COLUMN IF NOT EXISTS occupation VARCHAR(100)",
            "ALTER TABLE public.users ADD COLUMN IF NOT EXISTS language VARCHAR(10) DEFAULT 'en'",
            "ALTER TABLE public.users ADD COLUMN IF NOT EXISTS news_preferences JSON",
            "ALTER TABLE public.users ADD COLUMN IF NOT EXISTS subscription_status VARCHAR(20) DEFAULT 'free'",
            "ALTER TABLE public.users ADD COLUMN IF NOT EXISTS role VARCHAR(20) DEFAULT 'user'",
            "ALTER TABLE public.users ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now()",
        ]
        for migration_sql in user_column_migrations:
            await connection.execute(text(migration_sql))

        await connection.run_sync(Base.metadata.create_all)

    asyncio.create_task(start_webhook_proxy_loop())


@app.get("/health")
async def health():
    """Return the application health status."""
    return {"status": "ok", "app": "LOMINII"}


@app.websocket("/ws/games/{room_id}")
async def game_websocket(websocket: WebSocket, room_id: str):
    """Relay messages between connected players in an active game."""
    session = active_sessions.get(room_id)

    if session is None:
        await websocket.close(code=1008)
        return

    await websocket.accept()

    connections = session.setdefault("connections", [])

    if websocket not in connections:
        connections.append(websocket)

    try:
        while True:
            data = await websocket.receive_text()

            for connection in list(connections):
                if connection is websocket:
                    continue

                try:
                    await connection.send_text(data)
                except Exception:
                    if connection in connections:
                        connections.remove(connection)

    except WebSocketDisconnect:
        if websocket in connections:
            connections.remove(websocket)

        if not connections:
            session.pop("connections", None)


app.mount(
    "/",
    StaticFiles(directory="public", html=True),
    name="static",
)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
