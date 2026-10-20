"""Sportmonks live football scores and LOMINII notifications."""

import asyncio
import os
from datetime import datetime

import httpx

from .notifications import broadcast_notification


API_KEY = os.getenv("SPORTMONK_API_KEY", "")
LIVESCORE_URL = os.getenv(
    "SPORTMONK_LIVE_URL",
    "https://api.sportmonks.com/v3/football/livescores/inplay",
)

MATCH_STATE_CACHE = {}


def _name(value, fallback=""):
    """Extract a display name from an API object or string."""
    if isinstance(value, dict):
        return str(value.get("name") or fallback)
    return str(value or fallback)


def _participants(match):
    """Return home and away participant names."""
    home = "Home Team"
    away = "Away Team"

    for participant in match.get("participants") or []:
        location = str(participant.get("meta", {}).get("location", "")).lower()
        name = _name(participant, "Unknown Team")

        if location == "home":
            home = name
        elif location == "away":
            away = name

    if home == "Home Team" or away == "Away Team":
        match_name = match.get("name", "")
        if isinstance(match_name, str) and " vs " in match_name:
            left, right = match_name.split(" vs ", 1)
            home = left.strip() if home == "Home Team" else home
            away = right.strip() if away == "Away Team" else away

    return home, away


def _score(match):
    """Extract participant scores from the Sportmonks response."""
    scores = match.get("scores") or []

    if isinstance(scores, dict):
        home_score = scores.get("localteam_score", 0)
        away_score = scores.get("visitorteam_score", 0)
        return f"{home_score} - {away_score}"

    home_id = None
    away_id = None

    for participant in match.get("participants") or []:
        location = str(participant.get("meta", {}).get("location", "")).lower()
        if location == "home":
            home_id = participant.get("id")
        elif location == "away":
            away_id = participant.get("id")

    home_score = 0
    away_score = 0

    for item in scores:
        score_data = item.get("score") or {}
        goals = score_data.get("goals", 0)
        participant_id = item.get("participant_id")

        try:
            goals = int(goals or 0)
        except (TypeError, ValueError):
            goals = 0

        if participant_id == home_id:
            home_score = goals
        elif participant_id == away_id:
            away_score = goals

    return f"{home_score} - {away_score}"


def _event_type(event):
    """Normalize the various event-type representations."""
    event_type = event.get("type") or event.get("type_name") or ""

    if isinstance(event_type, dict):
        event_type = event_type.get("name", "")

    normalized = str(event_type).strip().upper().replace(" ", "_")

    if "GOAL" in normalized and "DISALLOWED" not in normalized:
        return "GOAL"
    if "YELLOW" in normalized:
        return "YELLOWCARD"
    if "RED" in normalized:
        return "REDCARD"

    return ""


async def get_live_scores(competition=None):
    """Fetch current in-play fixtures from Sportmonks API v3."""
    if not API_KEY:
        print(f"[{datetime.now()}] SPORTMONK_API_KEY missing.")
        return []

    params = {
        "api_token": API_KEY,
        "include": "events;scores;participants;state;league",
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(LIVESCORE_URL, params=params)
            response.raise_for_status()
            payload = response.json()

        matches = payload.get("data", [])
        if isinstance(matches, dict):
            matches = [matches]
        if not isinstance(matches, list):
            return []

        if competition:
            query = str(competition).strip().lower()

            def matches_competition(match):
                league = match.get("league") or {}
                league_name = _name(league).lower()
                league_id = str(match.get("league_id", "")).lower()
                match_name = str(match.get("name", "")).lower()

                return (
                    query == league_id
                    or query in league_name
                    or query in match_name
                )

            matches = [
                match for match in matches
                if matches_competition(match)
            ]

        return matches

    except (httpx.HTTPError, ValueError) as exc:
        print(f"[{datetime.now()}] Sportmonks request failed: {exc}")
        return []


async def dispatch_live_event(payload):
    """Persist a match-event notification for subscribed users."""
    title = payload.get("match_title", "Live Match")
    body = (
        f"{payload.get('display_text', 'Match update')} "
        f"| Score: {payload.get('current_score', '')}"
    )

    data = {
        "url": f"/sports?match={payload.get('match_id')}",
    }

    try:
        count = await broadcast_notification(title, body, data)
        print(
            f"[{datetime.now()}] Match notification processed: "
            f"{title}; subscribers notified: {count}"
        )
    except Exception as exc:
        print(f"[{datetime.now()}] Notification delivery failed: {exc}")


async def check_live_updates():
    """Detect new goals and cards in currently live fixtures."""
    matches = await get_live_scores()
    if not matches:
        return

    active_match_ids = set()

    for match in matches:
        match_id = str(match.get("id", ""))
        if not match_id:
            continue

        active_match_ids.add(match_id)

        events = match.get("events") or []
        if not isinstance(events, list):
            events = []

        current_score = _score(match)
        home_team, away_team = _participants(match)

        if match_id not in MATCH_STATE_CACHE:
            MATCH_STATE_CACHE[match_id] = {
                "processed_event_ids": {
                    str(event.get("id"))
                    for event in events
                    if event.get("id") is not None
                },
                "last_score": current_score,
            }
            continue

        cache = MATCH_STATE_CACHE[match_id]

        for event in sorted(
            events,
            key=lambda item: (
                item.get("minute") or 0,
                item.get("sort_order") or 0,
            ),
        ):
            event_id = event.get("id")
            if event_id is None:
                event_id = (
                    f"{event.get('type')}:{event.get('minute')}:"
                    f"{event.get('player_id')}"
                )

            event_id = str(event_id)

            if event_id in cache["processed_event_ids"]:
                continue

            cache["processed_event_ids"].add(event_id)

            event_type = _event_type(event)
            if event_type not in {"GOAL", "YELLOWCARD", "REDCARD"}:
                continue

            minute = event.get("minute")
            info = (
                event.get("info")
                or event.get("addition")
                or event_type.replace("_", " ").title()
            )

            await dispatch_live_event({
                "match_id": match_id,
                "match_title": f"{home_team} vs {away_team}",
                "current_score": current_score,
                "update_type": event_type,
                "timeline_minute": minute,
                "display_text": f"{info} at {minute}'" if minute is not None else str(info),
            })

        cache["last_score"] = current_score

    for match_id in list(MATCH_STATE_CACHE):
        if match_id not in active_match_ids:
            del MATCH_STATE_CACHE[match_id]


async def start_webhook_proxy_loop():
    """Poll Sportmonks continuously without stopping FastAPI startup."""
    print(f"[{datetime.now()}] Sportmonks live-score proxy started.")

    while True:
        try:
            await check_live_updates()
        except Exception as exc:
            print(f"[{datetime.now()}] Live-score polling failed: {exc}")

        await asyncio.sleep(12)


if __name__ == "__main__":
    try:
        asyncio.run(start_webhook_proxy_loop())
    except KeyboardInterrupt:
        print("\nProxy shut down gracefully.")
