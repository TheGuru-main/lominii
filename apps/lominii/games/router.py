"""LOMINII Games Room – REST API for game management"""
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from platform.database import get_db
from platform.invitation_service import (
    create_invitation,
    get_invitation,
    accept_invitation,
    decline_invitation,
    user_pending_invitations,
)
from platform.auth import get_current_user
from platform.models import User, GameSession, Leaderboard
from platform.game_engine import (
    create_room, join_room, leave_room, get_session,
    enter_matchmaking, leave_matchmaking
)
import json

router = APIRouter(prefix="/api/games", tags=["Games"])

# ── List available games

VALID_GAMES = {
    "ludo",
    "chess",
    "draft",
    "snooker",

}

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

# ────────────────────────────────────────────────
# Invitations
# ────────────────────────────────────────────────

@router.post("/invite")
async def send_game_invitation(
    request: Request,
    email: str = Depends(get_current_user),
):
    data = await request.json()

    receiver_id = data.get("receiver_id")
    game_id = data.get("game_id")

    if game_id not in VALID_GAMES:
        raise HTTPException(status_code=400, detail="Invalid game")

    if not receiver_id:
        raise HTTPException(status_code=400, detail="receiver_id is required")

    if not game_id:
        raise HTTPException(status_code=400, detail="game_id is required")

    invitation = await create_invitation(
        sender_id=email,
        receiver_id=receiver_id,
        workspace="games",
        destination=game_id,
        payload=data.get("payload", {})
    )

    return invitation


@router.get("/invite")
async def my_game_invitations(
    email: str = Depends(get_current_user),
):
    return await user_pending_invitations(email)


@router.get("/invite/{invitation_id}")
async def invitation_details(
    invitation_id: str,
):
    invitation = await get_invitation(invitation_id)

    if invitation is None:
        raise HTTPException(status_code=404, detail="Invitation not found")

    return invitation


@router.post("/invite/{invitation_id}/accept")
async def accept_game_invitation(
    invitation_id: str,
    email: str = Depends(get_current_user),
):
    invitation = await get_invitation(invitation_id)

    if invitation is None:
        raise HTTPException(status_code=404, detail="Invitation not found")

    if invitation["receiver_id"] != email:
        raise HTTPException(status_code=403, detail="Not your invitation")

    await accept_invitation(invitation_id)

    room_id = await create_room(
        invitation["destination"],
        invitation["sender_id"]
    )

    await join_room(room_id, invitation["receiver_id"])

    return {
        "status": "accepted",
        "room_id": room_id,
        "game_id": invitation["destination"],
    }


@router.post("/invite/{invitation_id}/decline")
async def decline_game_invitation(
    invitation_id: str,
    email: str = Depends(get_current_user),
):
    invitation = await get_invitation(invitation_id)

    if invitation is None:
        raise HTTPException(status_code=404, detail="Invitation not found")

    if invitation["receiver_id"] != email:
        raise HTTPException(status_code=403, detail="Not your invitation")

    return await decline_invitation(invitation_id)

# ── Leaderboard ───────────────────────────────────────
@router.get("/{game_id}/leaderboard")
async def leaderboard(game_id: str, db: AsyncSession = Depends(get_db)):
    top = (await db.execute(
        select(Leaderboard).where(Leaderboard.game_id == game_id).order_by(Leaderboard.points.desc()).limit(20)
    )).scalars().all()
    return [{"user_email": row.user_email, "points": row.points, "wins": row.wins} for row in top]
