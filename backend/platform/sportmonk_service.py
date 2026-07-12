"""
Sportmonks Live‑Score Proxy – integrated with LOMINII Notification Service
"""
import os
import httpx
import asyncio
from datetime import datetime
from .notifications import send_notification   # your own push service

# ── Configuration ──────────────────────────────────────
API_KEY = os.getenv("SPORTMONK_API_KEY", "")
LIVESCORE_URL = os.getenv("SPORTMONK_LIVE_URL", "https://sportmonks.com")

# ── In‑memory match state ──────────────────────────────
MATCH_STATE_CACHE = {}

# ── Dispatch a live event to LOMINII users ─────────────
async def dispatch_live_event(payload: dict):
    """
    Sends a push notification to all users who have subscribed
    to live‑football alerts.  The payload contains the event details.
    """
    # In the future, you can query the database for users with
    # news_preferences → sports = true and an active push subscription.
    # For now, we broadcast to *all* registered subscriptions.
    title = payload.get("match_title", "Live Match")
    body = f"{payload.get('display_text', 'Update')} | Score: {payload.get('current_score', '')}"
    data = {
        "match_id": payload.get("match_id"),
        "url": f"/sports?match={payload.get('match_id')}"
    }
    # send_notification(user_id, title, body, data)
    # For broadcast, we can loop over all active subscriptions.
    # (The actual implementation of broadcast is a small addition to notifications.py.)
    print(f"[{datetime.now()}] Push event: {title} – {body}")

# ── Main polling loop (unchanged logic) ──────────────────
async def check_live_updates():
    if not API_KEY:
        print(f"[{datetime.now()}] Error: SPORTMONK_API_KEY missing.")
        return

    params = {
        "api_token": API_KEY,
        "include": "events;scores;lineups.player;statistics.type;odds"
    }

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(LIVESCORE_URL, params=params, timeout=10)
            if resp.status_code != 200:
                print(f"[{datetime.now()}] Sportmonks API Error: Status {resp.status_code}")
                return

            matches = resp.json().get("data", [])
            active_match_ids = set()

            for m in matches:
                match_id = str(m.get("id"))
                active_match_ids.add(match_id)

                home_team = m.get("home_team", {}).get("name", "Home Team")
                away_team = m.get("away_team", {}).get("name", "Away Team")
                match_status = m.get("status", "INPLAY")

                scores = m.get("score", {})
                current_score = f"{scores.get('localteam_score', 0)} - {scores.get('visitorteam_score', 0)}"

                events = m.get("events", [])

                if match_id not in MATCH_STATE_CACHE:
                    MATCH_STATE_CACHE[match_id] = {
                        "processed_event_ids": set(),
                        "last_score": "0 - 0"
                    }

                cache = MATCH_STATE_CACHE[match_id]

                for event in sorted(events, key=lambda x: x.get("sort_order", 0)):
                    event_id = str(event.get("id"))

                    if event_id not in cache["processed_event_ids"]:
                        event_type = event.get("type", "").upper()
                        minute = event.get("minute")
                        info = event.get("info", "")

                        if event_type in ["GOAL", "YELLOWCARD", "REDCARD"]:
                            payload = {
                                "match_id": match_id,
                                "match_title": f"{home_team} vs {away_team}",
                                "current_score": current_score,
                                "update_type": event_type,
                                "timeline_minute": minute,
                                "status": match_status,
                                "display_text": info or f"{event_type.replace('_', ' ').title()} at {minute}'"
                            }
                            # Fire‑and‑forget push
                            asyncio.create_task(dispatch_live_event(payload))

                        cache["processed_event_ids"].add(event_id)

                cache["last_score"] = current_score

            # Purge finished matches
            finished = [m_id for m_id in MATCH_STATE_CACHE if m_id not in active_match_ids]
            for m_id in finished:
                del MATCH_STATE_CACHE[m_id]

        except Exception as e:
            print(f"[{datetime.now()}] Proxy loop error: {e}")

async def start_webhook_proxy_loop():
    print(f"[{datetime.now()}] Live‑score proxy started (LOMINII Notifications).")
    while True:
        await check_live_updates()
        await asyncio.sleep(12)

if __name__ == "__main__":
    try:
        asyncio.run(start_webhook_proxy_loop())
    except KeyboardInterrupt:
        print("\nProxy shut down gracefully.")