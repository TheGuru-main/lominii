"""
Game Engine Service – session, matchmaking, rewards, achievements
"""
import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

# In‑memory stores (replace with Redis/DB in production)
active_sessions: Dict[str, dict] = {}          # room_id -> game state
waiting_queues: Dict[str, List[str]] = {}       # game_id -> list of player_ids

async def create_room(game_id: str, host_id: str) -> str:
    """Create a new game room and return the room_id."""
    room_id = f"{game_id}-{uuid.uuid4().hex[:6]}"
    session = {
        "room_id": room_id,
        "game_id": game_id,
        "players": [host_id],
        "state": "waiting",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    active_sessions[room_id] = session
    return room_id

async def join_room(room_id: str, player_id: str) -> bool:
    """Add a player to an existing room. Return True if successful."""
    session = active_sessions.get(room_id)
    if not session or session["state"] != "waiting":
        return False
    if player_id in session["players"]:
        return True  # already joined
    session["players"].append(player_id)
    # Example: start game when 2 players (customisable per game)
    if len(session["players"]) >= 2:
        session["state"] = "playing"
    return True

async def leave_room(room_id: str, player_id: str):
    """Remove a player from a room. Delete room if empty."""
    session = active_sessions.get(room_id)
    if not session:
        return
    if player_id in session["players"]:
        session["players"].remove(player_id)
    if not session["players"]:
        active_sessions.pop(room_id, None)

async def get_session(room_id: str) -> Optional[dict]:
    return active_sessions.get(room_id)

# ---------- Simple matchmaking (queue) ----------
async def enter_matchmaking(game_id: str, player_id: str):
    if game_id not in waiting_queues:
        waiting_queues[game_id] = []
    queue = waiting_queues[game_id]
    if player_id not in queue:
        queue.append(player_id)
    # If enough players, create a room and remove them from queue
    if len(queue) >= 2:
        p1 = queue.pop(0)
        p2 = queue.pop(0)
        room_id = await create_room(game_id, p1)
        await join_room(room_id, p2)
        return room_id
    return None

async def leave_matchmaking(game_id: str, player_id: str):
    if game_id in waiting_queues:
        queue = waiting_queues[game_id]
        if player_id in queue:
            queue.remove(player_id)

# ---------- Rewards & Achievements (stubs) ----------
async def grant_reward(db, user_id: str, game_id: str, reward_type: str, amount: int, description: str = ""):
    """Insert a reward record. (Requires db session)"""
    from platform.models import GameReward
    reward = GameReward(user_id=user_id, game_id=game_id, reward_type=reward_type,
                        amount=amount, description=description)
    db.add(reward)
    await db.commit()

async def unlock_achievement(db, user_id: str, game_id: str, key: str):
    """Unlock an achievement if not already unlocked."""
    from platform.models import GameAchievement
    from sqlalchemy import select
    existing = (await db.execute(
        select(GameAchievement).where(
            GameAchievement.user_id == user_id,
            GameAchievement.game_id == game_id,
            GameAchievement.achievement_key == key
        )
    )).scalar_one_or_none()
    if not existing:
        ach = GameAchievement(user_id=user_id, game_id=game_id, achievement_key=key)
        db.add(ach)
        await db.commit()