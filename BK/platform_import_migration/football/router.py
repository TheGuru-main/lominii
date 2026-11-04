"""Football Live Scores Router (Sportmonk)"""
from fastapi import APIRouter
from platform.sportmonk_service import get_live_scores

router = APIRouter(prefix="/api/football", tags=["Football"])

@router.get("/scores")
async def live_scores(competition: str = None):
    matches = await get_live_scores(competition)
    return {"matches": matches}