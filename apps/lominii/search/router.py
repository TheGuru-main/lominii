"""LOMINII Search Room – Unified Search Router (Real DB + GSG + Cache + Live AI)"""
import asyncio
import hashlib
import httpx
from datetime import datetime, timedelta
from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from platform.gsp import normalise, calculate_lsum, calculate_ssum, first_letter_index, gsp_place, elastic_cloud
from platform.prompts import get_prompt
from platform.content_filter import is_blocked, is_ai_blocked
from platform.auth import get_current_user
from platform.database import get_db
from platform.gsg import gps_to_gsg
from platform.intent_analyzer import analyze
from platform.models.public import User,
from platform.models.search import (
    Search,
    Trending,
    Correction,
    NewsArticle,
    NewsCache,
    DictionaryCache,
    SearchCache,
    VideoCache,
)

router = APIRouter(prefix="/api/search", tags=["Search"])

CACHE_TTL_ANONYMOUS = 5
CACHE_TTL_AUTHENTICATED = 300

# Hugging Face free inference endpoint (model for summarization)
HF_API_URL = "https://api-inference.huggingface.co/models/facebook/bart-large-cnn"
HF_HEADERS = {"Authorization": f"Bearer {os.getenv('HF_API_KEY', '***&&&@')}"} if os.getenv('HF_API_KEY') else {}


def build_cache_key(query: str, lang: str, domain: str) -> str:
    raw = f"{query}|{lang}|{domain}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


async def call_ai_model(prompt: str) -> str:
    """Call Hugging Face inference API and return the summary text, or a fallback."""
    if not HF_HEADERS:
        return "AI summary unavailable (API key not configured)."
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(HF_API_URL, headers=HF_HEADERS, json={"inputs": prompt})
            if resp.status_code == 200:
                data = resp.json()
                # Response format varies; handle list or dict
                if isinstance(data, list) and len(data) > 0:
                    return data[0].get("summary_text", data[0])
                elif isinstance(data, dict):
                    return data.get("summary_text", str(data))
            # Fallback for non‑200 responses
            return "AI summarization is temporarily unavailable."
    except Exception:
        return "AI summarization is temporarily unavailable."


@router.post("/")
async def unified_search(
    request: Request,
    email: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    data = await request.json()
    query = data.get("q", "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="Missing query")

    # 1. Content filtering
    if is_blocked(query):
        raise HTTPException(status_code=400, detail="Blocked query")

    # 2. User context
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    lang = user.language if user and user.language else "en"
    country = "Nigeria"   # can be extended
    tier = user.subscription_status if user else "free"

    # 3. Normalisation
    norm_query = normalise(query, lang)

    # 4. Intent / domain
    ctx = analyze(norm_query)
    domain = ctx["domain"]

    # 5. Cache key & lookup
    cache_key = build_cache_key(norm_query, lang, domain)
    cached = (await db.execute(
        select(SearchCache).where(SearchCache.cache_key == cache_key)
    )).scalar_one_or_none()

    ttl = CACHE_TTL_AUTHENTICATED if user else CACHE_TTL_ANONYMOUS
    if cached and (datetime.utcnow() - cached.cached_at) < timedelta(minutes=ttl):
        return cached.result

    # 6. GSP placement (word‑based)
    L = calculate_lsum(norm_query, lang)
    S = calculate_ssum(norm_query, lang)
    c = first_letter_index(norm_query, lang)
    gsp = gsp_place(L, S, c, K=5)
    cloud = elastic_cloud(L, S, c, radius=1, first_letter_radius=1)
    primary = gsp["primary_cell"]

    # 7. GSG cell (location‑aware, additive)
    gsg_data = None
    lat = data.get("lat")
    lon = data.get("lon")
    if lat is not None and lon is not None:
        try:
            gsg_cell, (gsg_L, gsg_S, gsg_c) = gps_to_gsg(float(lat), float(lon))
            gsg_data = {
                "grid_x": gsg_cell[0],
                "grid_y": gsg_cell[1],
                "cell_id": f"city.{gsg_cell[0]}.{gsg_cell[1]}"
            }
        except Exception:
            gsg_data = None

    # 8. Fetch external sources (parallel)
    async with httpx.AsyncClient() as client:
        dict_url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{norm_query}"
        news_url = f"https://gnews.io/api/v4/search?q={norm_query}&lang=en&max=6&apikey=demo"
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

    # 9. AI Summary (real model call)
    ai_summary = None
    if not is_ai_blocked(query):
        prompt_template = get_prompt(tier)
        sources = f"Dictionary: {definition or 'None'}\nNews: {news_articles}"
        prompt = prompt_template.format(query=norm_query, sources=sources, country=country, language=lang)
        ai_summary = await call_ai_model(prompt)
    else:
        ai_summary = None

    # 10. Build response
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
        "did_you_mean": None,
        "related_questions": [],
        "gsg_cell": gsg_data
    }

    # 11. Persist search and update cache
    if user:
        new_search = Search(user_id=user.id, query=query,
                            gsp_cell=f"{primary['col']},{primary['row']}")
        db.add(new_search)

    if cached:
        cached.result = response
        cached.cached_at = datetime.utcnow()
    else:
        cache_entry = SearchCache(cache_key=cache_key, result=response,
                                  cached_at=datetime.utcnow())
        db.add(cache_entry)
    await db.commit()

    return response
