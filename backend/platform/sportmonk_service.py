"""Sportmonk Live Football Service (Platform Layer - Extended)"""
import os
import httpx

API_KEY = os.getenv("SPORTMONK_API_KEY", "")
BASE_URL = os.getenv("SPORTMONK_BASE_URL", "https://api.sportmonks.com/v3/football")

async def get_live_scores_extended(competition: str = None) -> list:
    """Fetch live football scores, events, lineups, statistics, and betting odds from Sportmonks v3."""
    if not API_KEY:
        return []
        
    headers = {"Authorization": API_KEY}   
    url = f"{BASE_URL}/matches"
    
    # Comma-separated string combining all related entities in one pass
    # Using nested includes (e.g. statistics.type) to retrieve explicit metric names
    includes = "events;lineups.player;statistics.type;odds"
    
    params = {"include": includes}
    if competition:
        params["competition"] = competition
        
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, headers=headers, params=params, timeout=12)
            if resp.status_code != 200:
                return []
                
            data = resp.json()
            matches = data.get("data", [])
            result_payload = []
            
            for m in matches:
                # 1. Map Core Match Data & Score
                scores = m.get("score", {})
                current_score = f"{scores.get('localteam_score', 0)} - {scores.get('visitorteam_score', 0)}"
                
                # 2. Extract and Process Events
                events = sorted(m.get("events", []), key=lambda x: x.get("sort_order", 0))
                timeline = []
                yellow_cards = 0
                red_cards = 0
                
                for e in events:
                    event_type = e.get("type", "").upper()
                    if event_type == "YELLOWCARD":
                        yellow_cards += 1
                    elif event_type == "REDCARD":
                        red_cards += 1
                        
                    timeline.append({
                        "type": event_type,
                        "minute": e.get("minute"),
                        "description": e.get("info", "")
                    })
                
                # 3. Extract Lineups (Differentiating starters from substitutes)
                lineup_data = m.get("lineups", [])
                lineups = {"home": {"starting": [], "bench": []}, "away": {"starting": [], "bench": []}}
                
                for player_entry in lineup_data:
                    # Determine team orientation
                    team_side = "home" if player_entry.get("team_id") == m.get("localteam_id") else "away"
                    
                    player_info = {
                        "name": player_entry.get("player", {}).get("name", "Unknown Player"),
                        "jersey_number": player_entry.get("jersey_number"),
                        "position": player_entry.get("position", {}).get("name", "N/A")
                    }
                    
                    # Sportmonks v3 typically exposes a 'formation_position' or 'is_starter' boolean
                    if player_entry.get("formation_position") is not None:
                        lineups[team_side]["starting"].append(player_info)
                    else:
                        lineups[team_side]["bench"].append(player_info)

                # 4. Extract In-Play Live Match Statistics
                stats_entries = m.get("statistics", [])
                match_stats = {"home": {}, "away": {}}
                
                for stat in stats_entries:
                    team_side = "home" if stat.get("team_id") == m.get("localteam_id") else "away"
                    # Using statistics.type nested mapping for metric identity
                    stat_name = stat.get("type", {}).get("name", "unknown").lower().replace(" ", "_")
                    stat_value = stat.get("value")
                    
                    if stat_name != "unknown":
                        match_stats[team_side][stat_name] = stat_value

                # 5. Extract Dynamic Odds Marketplace Data
                odds_entries = m.get("odds", [])
                market_odds = []
                
                for odd in odds_entries:
                    market_odds.append({
                        "market_name": odd.get("market_name", "Match Winner"),
                        "label": odd.get("label"), # e.g. "1", "X", "2", "Over 2.5"
                        "value": odd.get("value")  # Decimal Odds
                    })

                # Consolidated Match Node
                result_payload.append({
                    "id": m.get("id"),
                    "home_team": m.get("home_team", {}).get("name", "Home Team"),
                    "away_team": m.get("away_team", {}).get("name", "Away Team"),
                    "score": current_score,
                    "status": m.get("status", "SCHEDULED"),
                    "yellow_cards_total": yellow_cards,
                    "red_cards_total": red_cards,
                    "events_timeline": timeline,
                    "lineups": lineups,
                    "live_statistics": match_stats,
                    "odds": market_odds
                })
                
            return result_payload
        except Exception:
            pass
            
    return []
