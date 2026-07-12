"""Sportmonks Proxy Webhook Dispatcher Engine"""
import os
import httpx
import asyncio
from datetime import datetime

# API Configurations
API_KEY = os.getenv("SPORTMONK_API_KEY", "")
LIVESCORE_URL = os.getenv("SPORTMONK_LIVE_URL", "https://api.sportmonks.com/v3/football/livescores/inplay")

# Platform Internal Notifications Routing 
NOTIFICATION_MANAGER_WEBHOOK = "https://yourdomain.com"
INTERNAL_AUTH_SECRET = os.getenv("INTERNAL_WEBHOOK_SECRET", "super-secure-token")

# Local application state cache to prevent duplicate alerts
MATCH_STATE_CACHE = {}

async def dispatch_to_notification_manager(payload: dict):
    """Dispatches a clean event payload directly to your Notification Manager."""
    headers = {
        "Content-Type": "application/json",
        "X-Internal-Secret": INTERNAL_AUTH_SECRET
    }
    async with httpx.AsyncClient() as client:
        try:
            # Pushing instant JSON payload to your platform layer
            response = await client.post(NOTIFICATION_MANAGER_WEBHOOK, json=payload, headers=headers, timeout=5)
            print(f"[{datetime.now()}] Webhook routed status: {response.status_code}")
        except Exception as e:
            print(f"[{datetime.now()}] Failed routing to notification manager: {str(e)}")

async def check_live_updates():
    """Polls Sportmonks inplay, filters state deltas, and synthesizes push packets."""
    if not API_KEY:
        return

    # Use explicit includes to keep payload efficient
    params = {
        "api_token": API_KEY,
        "include": "events;scores"
    }

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(LIVESCORE_URL, params=params, timeout=8)
            if resp.status_code != 200:
                return

            matches = resp.json().get("data", [])

            for m in matches:
                match_id = str(m.get("id"))
                home_team = m.get("home_team", {}).get("name", "Home Team")
                away_team = m.get("away_team", {}).get("name", "Away Team")
                
                # Dynamic Score Parsing
                scores = m.get("score", {})
                current_score = f"{scores.get('localteam_score', 0)} - {scores.get('visitorteam_score', 0)}"
                
                # Fetch raw events
                events = m.get("events", [])
                
                # Initialize caching context if match is newly live
                if match_id not in MATCH_STATE_CACHE:
                    MATCH_STATE_CACHE[match_id] = {
                        "processed_event_ids": set(),
                        "last_score": "0 - 0"
                    }

                cache = MATCH_STATE_CACHE[match_id]

                # Trace timeline anomalies chronologically
                for event in sorted(events, key=lambda x: x.get("sort_order", 0)):
                    event_id = str(event.get("id"))
                    
                    # If this event id hasn't been cached yet, trigger notification push
                    if event_id not in cache["processed_event_ids"]:
                        event_type = event.get("type", "").upper()
                        minute = event.get("minute")
                        info = event.get("info", "")

                        # Construct a normalized payload for your notification manager
                        if event_type in ["GOAL", "YELLOWCARD", "REDCARD"]:
                            webhook_payload = {
                                "event_channel": "live_football_feed",
                                "match_id": match_id,
                                "match_title": f"{home_team} vs {away_team}",
                                "current_score": current_score,
                                "update_type": event_type,
                                "timeline_minute": minute,
                                "display_text": info or f"{event_type.replace('_', ' ').title()} at {minute}'"
                            }
                            
                            # Fire-and-forget payload handling to your notification service
                            asyncio.create_task(dispatch_to_notification_manager(webhook_payload))
                        
                        # Add to processed ledger
                        cache["processed_event_ids"].add(event_id)
                
                # Update cached score state
                cache["last_score"] = current_score

        except Exception as e:
            print(f"Error handling proxy iteration loop: {str(e)}")

async def start_webhook_proxy_loop():
    """Runs continuous rapid inplay polling loops safely."""
    print("Proxy Webhook system ignited. Pushing to Platform Notification Manager...")
    while True:
        await check_live_updates()
        # Inplay metrics are optimized at 10-15s windows safely staying within rate limits
        await asyncio.sleep(12) 
