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
from apps.lominii.social.router import router as social_router
from apps.lominii.auth.router import router as auth_router
from apps.lominii.admin.router import router as admin_router
from platform.database import engine, Base

app = FastAPI(title="LOMINII Platform", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(search_router)
app.include_router(social_router)
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(football_router)
app.mount("/", StaticFiles(directory="public", html=True), name="static")

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.get("/health")
async def health():
    return {"status": "ok", "app": "LOMINII"}

from fastapi import WebSocket, WebSocketDisconnect
from collections import defaultdict
import json

# room_id -> connected websockets
game_rooms = defaultdict(set)

@app.websocket("/ws/games/{game_id}/{room_id}")
async def game_websocket(websocket: WebSocket, room_id: str):
    await websocket.accept()

    game_rooms[room_id].add(websocket)

    try:
        while True:
            data = await websocket.receive_text()

            # Broadcast to every player in the room except the sender
            for client in list(game_rooms[room_id]):
                if client != websocket:
                    await client.send_text(data)

    except WebSocketDisconnect:
        game_rooms[room_id].discard(websocket)

        if not game_rooms[room_id]:
            del game_rooms[room_id]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)