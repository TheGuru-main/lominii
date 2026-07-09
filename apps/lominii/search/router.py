"""LOMINII Search Room – Unified Search Router"""
import asyncio
import hashlib
import httpx
from fastapi import APIRouter, Request, HTTPException, Depends
from platform.gsp import normalise, calculate_lsum, calculate_ssum, first_letter_index, gsp_place, elastic_cloud
from platform.prompts import get_prompt, detect_domain
from platform.content_filter import is_blocked, is_ai_blocked
from platform.auth import get_current_user  # requires valid BubbleJumbo token

router = APIRouter(prefix="/api/search", tags=["Search"])

# ---------------------------------------------------------------------------
# Mock database helpers – replace with real DB calls when models are ready
# ---------------------------------------------------------------------------
async def get_user_subscription(email: str) -> str:
    # TODO: query DB for subscription_status; return 'free' or 'premium'
    return "free"

async def get_user_language(email: str) -> str:
    # TODO: return user's preferred language, default 'en'
    return "en"

async def get_user_country(email: str) -> str:
    # TODO: geolocate or return from profile; default 'Nigeria'
    return "Nigeria"

# ---------------------------------------------------------------------------
# Unified Search Endpoint
# ---------------------------------------------------------------------------
@router.post("/")
async def unified_search(request: Request, email: str = Depends(get_current_user)):
    data = await request.json()
    query = data.get("q", "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="Missing query")

    # 1. Content filtering
    if is_blocked(query):
        raise HTTPException(status_code=400, detail="Blocked query")

    # 2. Language & user context
    lang = await get_user_language(email)
    country = await get_user_country(email)
    tier = await get_user_subscription(email)

    # 3. Normalisation (language‑aware)
    norm_query = normalise(query, lang)

    # 4. GSP placement (for caching, sponsored cells, etc.)
    L = calculate_lsum(norm_query, lang)
    S = calculate_ssum(norm_query, lang)
    c = first_letter_index(norm_query, lang)
    gsp = gsp_place(L, S, c, K=5)
    cloud = elastic_cloud(L, S, c, radius=1, first_letter_radius=1)
    primary = gsp["primary_cell"]

    # 5. Fetch external sources (parallel)
    async with httpx.AsyncClient() as client:
        dict_url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{norm_query}"
        news_url = f"https://gnews.io/api/v4/search?q={norm_query}&lang=en&max=6&apikey=demo"  # placeholder
        dict_task = client.get(dict_url)
        news_task = client.get(news_url)
        dict_resp, news_resp = await asyncio.gather(dict_task, news_task)

    definition = None
    if dict_resp.status_code == 200:
        dict_data = dict_resp.json()
        definition = dict_data[0]["meanings"][0]["definitions"][0]["definition"] if dict_data else None

    news_articles = []
    if news_resp.status_code == 200:
        news_data = news_resp.json()
        news_articles = [{"title": a["title"], "url": a["url"]} for a in news_data.get("articles", [])[:6]]

    # 6. AI Summary (if not blocked)
    ai_summary = None
    if not is_ai_blocked(query):
        prompt_template = get_prompt(tier)  # board_light or board
        sources = f"Dictionary: {definition or 'None'}\nNews: {news_articles}"
        prompt = prompt_template.format(query=norm_query, sources=sources, country=country, language=lang)
        # TODO: call Hugging Face inference API with 'prompt'
        # For now, return the prompt itself as placeholder
        ai_summary = prompt  # replace with actual AI call

    # 7. Build response
    response = {
        "query": query,
        "Lsum": L,
        "Ssum": S,
        "primary_cell_col": primary["col"],
        "primary_cell_row": primary["row"],
        "gsp": gsp,
        "elastic_cloud_size": len(cloud),
        "definition": definition,
        "news": news_articles,
        "ai_summary": ai_summary,
        "did_you_mean": None,   # TODO: implement from corrections table
        "related_questions": []  # TODO: from elastic cloud neighbours
    }
    return response