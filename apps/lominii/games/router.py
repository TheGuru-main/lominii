"""LOMINII Games Room – REST API for game management"""
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from platform.database import get_db
from platform.auth import get_current_user
from platform.models import User, GameSession, Leaderboard
from platform.game_engine import (
    create_room, join_room, leave_room, get_session,
    enter_matchmaking, leave_matchmaking
)
import json

router = APIRouter(prefix="/api/games", tags=["Games"])

# ── List available games ──────────────────────────────
@router.get("/")
async def list_games():
    return [
        {"id": "ludo", "name": "Ludo", "icon": "🎲", "min_players": 2, "max_players": 4},
        {"id": "chess", "name": "Chess", "icon": "♟️", "min_players": 2, "max_players": 2},
        {"id": "draft", "name": "Draft", "icon": "🟤", "min_players": 2, "max_players": 2},
        {"id": "snooker", "name": "Snooker", "icon": "🎱", "min_players": 2, "max_players": 2},
        {"id": "car_race", "name": "Car Race", "icon": "🏎️", "min_players": 1, "max_players": 8, "coming_soon": True},
        {"id": "sniper", "name": "Sniper", "icon": "🔫", "min_players": 1, "max_players": 4, "coming_soon": True},
        {"id": "edu_arcade", "name": "Edu Arcade", "icon": "🧩", "min_players": 1, "max_players": 1, "coming_soon": True},
    ]

# ── Create room ───────────────────────────────────────
@router.post("/{game_id}/rooms")
async def create_game_room(game_id: str, email: str = Depends(get_current_user)):
    user_id = email  # or fetch user.id; for simplicity use email as id
    room_id = await create_room(game_id, user_id)
    return {"room_id": room_id, "game_id": game_id, "status": "waiting"}

# ── Join room ─────────────────────────────────────────
@router.post("/{game_id}/rooms/{room_id}/join")
async def join_game_room(game_id: str, room_id: str, email: str = Depends(get_current_user)):
    success = await join_room(room_id, email)
    if not success:
        raise HTTPException(status_code=400, detail="Room not available")
    return {"status": "joined", "room_id": room_id}

# ── Get room status ───────────────────────────────────
@router.get("/{game_id}/rooms/{room_id}")
async def room_status(game_id: str, room_id: str):
    session = await get_session(room_id)
    if not session:
        raise HTTPException(status_code=404, detail="Room not found")
    return session

# ── Leave room ────────────────────────────────────────
@router.delete("/{game_id}/rooms/{room_id}/leave")
async def leave_game_room(game_id: str, room_id: str, email: str = Depends(get_current_user)):
    await leave_room(room_id, email)
    return {"status": "left"}

# ── Matchmaking (enter queue) ─────────────────────────
@router.post("/{game_id}/matchmaking/enter")
async def enter_queue(game_id: str, email: str = Depends(get_current_user)):
    room_id = await enter_matchmaking(game_id, email)
    if room_id:
        return {"status": "matched", "room_id": room_id}
    return {"status": "waiting"}

@router.post("/{game_id}/matchmaking/leave")
async def leave_queue(game_id: str, email: str = Depends(get_current_user)):
    await leave_matchmaking(game_id, email)
    return {"status": "left"}

# ── Leaderboard ───────────────────────────────────────
@router.get("/{game_id}/leaderboard")
async def leaderboard(game_id: str, db: AsyncSession = Depends(get_db)):
    top = (await db.execute(
        select(Leaderboard).where(Leaderboard.game_id == game_id).order_by(Leaderboard.points.desc()).limit(20)
    )).scalars().all()
    return [{"user_email": row.user_email, "points": row.points, "wins": row.wins} for row in top]