"""
LOMINII – Main FastAPI Application
Gurutech Platform Architecture – Shared Platform, Independent Modules
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from apps.lominii.search.router import router as search_router
from apps.lominii.football.router import router as football_router
from apps.lominii.games.router import router as games_router
from apps.lominii.social.router import router as social_router
from apps.lominii.auth.router import router as auth_router
from apps.lominii.admin.router import router as admin_router
from platform.sportmonk_service import start_webhook_proxy_loop 
import asyncio
from platform.database import engine, Base

app = FastAPI(title="LOMINII Platform", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(search_router)
app.include_router(social_router)
app.include_router(games_router)
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(football_router)
app.mount("/", StaticFiles(directory="public", html=True), name="static")

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Start the live‑score proxy as a background task (never blocks the API)
   asyncio.create_task(start_webhook_proxy_loop())

@app.get("/health")
async def health():
    return {"status": "ok", "app": "LOMINII"}

from fastapi import WebSocket, WebSocketDisconnect
import json

# room_id -> connected websockets
game_rooms = defaultdict(set)

from fastapi import WebSocket, WebSocketDisconnect
from platform.game_engine import active_sessions
import json

@app.websocket("/ws/games/{room_id}")
async def game_websocket(websocket: WebSocket, room_id: str):
    session = active_sessions.get(room_id)

    if session is None:
        await websocket.close(code=1008)
        return

    await websocket.accept()

    # Create socket list if it doesn't exist
    session.setdefault("connections", [])
    session["connections"].append(websocket)

    try:
        while True:
            data = await websocket.receive_text()

            # Broadcast to every connected player in this room
            for connection in list(session["connections"]):
                if connection != websocket:
                    try:
                        await connection.send_text(data)
                    except Exception:
                        session["connections"].remove(connection)

    except WebSocketDisconnect:
        if websocket in session["connections"]:
            session["connections"].remove(websocket)

        # Clean up if nobody is connected anymore
        if not session["connections"]:
            session.pop("connections", None)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)