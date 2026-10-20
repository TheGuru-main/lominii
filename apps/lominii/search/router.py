"""LOMINII Search Room – Unified Search Router (Real DB + GSG + Cache + Live AI)"""
import asyncio
import hashlib
import httpx
import os
from urllib.parse import quote
from datetime import datetime, timedelta
from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from lominii_platform.gsp import normalise, calculate_lsum, calculate_ssum, first_letter_index, gsp_place, elastic_cloud
from lominii_platform.ai.prompt_builder import build_prompt
from lominii_platform.ai.knowledge import (
    get_knowledge,
    save_knowledge,
)
from lominii_platform.content_filter import is_blocked, is_ai_blocked
from lominii_platform.auth import get_current_user
from lominii_platform.database import get_db
from lominii_platform.gsg import gps_to_gsg
from lominii_platform.intent_analyzer import analyze
from lominii_platform.ai.gateway import generate
from lominii_platform.wikipedia import search_wikipedia

# (public / search schemas)
from lominii_platform.models.public import User
from lominii_platform.models.search import (
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
GNEWS_API_KEY = os.getenv("GNEWS_API_KEY", "").strip()

CACHE_TTL_ANONYMOUS = 5
CACHE_TTL_AUTHENTICATED = 300


def build_cache_key(query: str, lang: str, domain: str) -> str:
    raw = f"{query}|{lang}|{domain}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


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
    dict_url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{quote(norm_query, safe='')}"
    dict_resp = None
    news_resp = None

    async with httpx.AsyncClient(timeout=10.0) as client:
        tasks = [client.get(dict_url)]
        if GNEWS_API_KEY:
            tasks.append(
                client.get(
                    "https://gnews.io/api/v4/search",
                    params={
                        "q": norm_query,
                        "lang": "en",
                        "max": 6,
                        "apikey": GNEWS_API_KEY,
                    },
                )
            )
        results = await asyncio.gather(*tasks, return_exceptions=True)

    if results and isinstance(results[0], httpx.Response):
        dict_resp = results[0]
    if len(results) > 1 and isinstance(results[1], httpx.Response):
        news_resp = results[1]

    definition = None
    if dict_resp is not None and dict_resp.status_code == 200:
        try:
            dict_data = dict_resp.json()
            definition = (
                dict_data[0]["meanings"][0]["definitions"][0]["definition"]
                if dict_data else None
            )
        except (ValueError, KeyError, IndexError, TypeError):
            definition = None

    news_articles = []
    if news_resp is not None and news_resp.status_code == 200:
        try:
            news_data = news_resp.json()
            news_articles = [
                {"title": a["title"], "url": a["url"]}
                for a in news_data.get("articles", [])[:6]
                if isinstance(a, dict) and a.get("title") and a.get("url")
            ]
        except (ValueError, KeyError, TypeError):
            news_articles = []

    # 8.5 Wikipedia — optional user preference
    wiki_articles = []
    preferences = user.news_preferences if user else {}

    if isinstance(preferences, dict) and preferences.get("wikipedia", False):
        try:
            wiki_articles = await search_wikipedia(
                norm_query,
                lang=lang,
                limit=3,
            )
        except Exception as exc:
            print(f"Wikipedia search failed: {exc}")
            wiki_articles = []

    # 9. AI Summary — skip when the query is blocked
    ai_summary = None

    if not is_ai_blocked(query):
        sources = f"""Dictionary: {definition or "None"}
News: {news_articles}
Wikipedia: {wiki_articles}"""

        try:
            prompt = build_prompt(
                query=norm_query,
                sources=sources,
                country=country,
                language=lang,
                tier=tier,
                workspace="search",
                intent=ctx.get("intent"),
            )

            ai_summary = await generate(
                prompt,
                intent=ctx.get("intent"),
                workspace="search",
                user_id=str(user.id) if user else None,
            )
        except Exception as exc:
            print(f"Search AI summary failed: {exc}")
            ai_summary = None

    # 9.5 Existing correction table — spelling suggestion
    correction = (
        await db.execute(
            select(Correction)
            .where(Correction.misspelled.ilike(norm_query))
            .order_by(Correction.confidence.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    did_you_mean = None
    if correction and correction.corrected.strip().lower() != norm_query.lower():
        did_you_mean = correction.corrected.strip()

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
        "wikipedia": wiki_articles,
        "ai_summary": ai_summary,
        "did_you_mean": did_you_mean,
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