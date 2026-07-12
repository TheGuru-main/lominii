"""Sportmonk Live Football Service (Platform Layer)"""
import os
import httpx

API_KEY = os.getenv("SPORTMONK_API_KEY", "")
BASE_URL = os.getenv("SPORTMONK_BASE_URL", "https://api.sportmonk.com/v3")

async def get_live_scores(competition: str = None) -> list:
    """Fetch live football scores from Sportmonk."""
    if not API_KEY:
        return []
    headers = {"Authorization": f"Bearer {API_KEY}"}   # Sportmonk uses Bearer token
    url = f"{BASE_URL}/matches"
    params = {}
    if competition:
        params["competition"] = competition
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, headers=headers, params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                matches = data.get("data", [])
                return [
                    {
                        "home_team": m.get("home_team", {}).get("name", "Home"),
                        "away_team": m.get("away_team", {}).get("name", "Away"),
                        "score": f"{m.get('score',{}).get('fulltime',0)} - {m.get('score',{}).get('fulltime',0)}",
                        "status": m.get("status", "SCHEDULED")
                    }
                    for m in matches
                ]
        except Exception:
            pass
    return []