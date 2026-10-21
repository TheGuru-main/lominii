"""LOMINII unified search: corrected GSP, independent sources, crawler index, and cache."""
import asyncio
import hashlib
import html
import httpx
import os
import re
from datetime import datetime, timedelta
from html.parser import HTMLParser
from urllib.parse import parse_qs, quote, urlencode, urlparse
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import case, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from lominii_platform.gsp import (calculate_lsum, calculate_ssum, calculate_uid_chain,
    elastic_cloud, first_letter_index, gsp_place, normalise)
from lominii_platform.ai.prompt_builder import build_prompt
from lominii_platform.content_filter import is_blocked, is_ai_blocked
from lominii_platform.auth import oauth2_scheme, validate_token
from lominii_platform.database import get_db
from lominii_platform.gsg import gps_to_gsg
from lominii_platform.intent_analyzer import analyze
from lominii_platform.ai.gateway import generate
from lominii_platform.wikipedia import search_wikipedia
from lominii_platform.models.public import User
from lominii_platform.models.search import Search, Correction, NewsArticle, NewsCache, DictionaryCache, SearchCache
from lominii_platform.models.crawler import CrawlerPage

router = APIRouter(prefix="/api/search", tags=["Search"])
GNEWS_API_KEY = os.getenv("GNEWS_API_KEY", "").strip()
SCRAPINGBEE_API_KEY = os.getenv("SCRAPINGBEE_API_KEY", "").strip()
CACHE_TTL_ANONYMOUS = 5
CACHE_TTL_AUTHENTICATED = 300
CACHE_VERSION = "search-gsp-v2"

async def get_search_identity(token: str = Depends(oauth2_scheme)) -> str:
    """Accept valid guest tokens for free search, not other protected routes."""
    payload = validate_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    identity = payload.get("sub")
    if not isinstance(identity, str) or not identity:
        raise HTTPException(status_code=401, detail="Invalid token identity")
    return identity


def build_cache_key(query: str, lang: str, domain: str) -> str:
    raw = f"{CACHE_VERSION}|{query}|{lang}|{domain}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


class _SearchResultParser(HTMLParser):
    """Extract external result anchors from a search-engine results page."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.current = None
        self.results = []
    def handle_starttag(self, tag, attrs):
        if tag.lower() != "a":
            return
        href = dict(attrs).get("href", "")
        if href.startswith("/url?"):
            params = parse_qs(urlparse(href).query)
            href = (params.get("q") or params.get("url") or [""])[0]
        if href.startswith(("http://", "https://")):
            self.current = [href, []]
    def handle_data(self, data):
        if self.current is not None and data.strip():
            self.current[1].append(data.strip())
    def handle_endtag(self, tag):
        if tag.lower() != "a" or self.current is None:
            return
        url, parts = self.current
        self.current = None
        title = re.sub(r"\s+", " ", " ".join(parts)).strip()
        try:
            host = (urlparse(url).hostname or "").lower()
        except ValueError:
            return
        blocked = ("google.com", "google.co.uk", "googleusercontent.com", "gstatic.com",
                   "bing.com", "microsoft.com", "scrapingbee.com")
        if not title or len(title) < 3 or not host or any(
            host == item or host.endswith("." + item) for item in blocked
        ):
            return
        if not any(item["url"] == url for item in self.results):
            self.results.append({"title": html.unescape(title)[:300], "url": url,
                                 "source": "Web search"})


def _parse_web_results(page: str, limit: int = 8) -> list[dict]:
    parser = _SearchResultParser()
    try:
        parser.feed(page or "")
    except Exception:
        return []
    return parser.results[:limit]


async def _scrapingbee_search(client: httpx.AsyncClient, query: str) -> list[dict]:
    """Call ScrapingBee only with a fixed search-provider URL, never a user URL."""
    if not SCRAPINGBEE_API_KEY:
        return []
    search_url = "https://www.google.com/search?" + urlencode({"q": query})
    try:
        response = await client.get("https://app.scrapingbee.com/api/v1/", params={
            "api_key": SCRAPINGBEE_API_KEY, "url": search_url,
            "render_js": "false", "block_ads": "true",
        }, timeout=httpx.Timeout(18.0, connect=4.0))
        if response.status_code != 200:
            return []
        return _parse_web_results(response.text, limit=8)
    except Exception as exc:
        print(f"ScrapingBee search source failed: {exc}")
        return []


async def _gnews_search(client: httpx.AsyncClient, query: str, lang: str) -> list[dict]:
    if not GNEWS_API_KEY:
        return []
    language = lang if lang in {"en", "fr", "de"} else "en"
    try:
        response = await client.get("https://gnews.io/api/v4/search", params={
            "q": query, "lang": language, "max": 6, "apikey": GNEWS_API_KEY,
        })
        if response.status_code != 200:
            return []
        articles = []
        for article in response.json().get("articles", [])[:6]:
            if not isinstance(article, dict) or not article.get("title") or not article.get("url"):
                continue
            source = article.get("source") or {}
            articles.append({"title": article["title"], "url": article["url"],
                "source": source.get("name") if isinstance(source, dict) else str(source),
                "published_at": article.get("publishedAt")})
        return articles
    except Exception as exc:
        print(f"GNews source failed: {exc}")
        return []


def _dictionary_payload(payload) -> tuple[str | None, dict | None]:
    if not isinstance(payload, list) or not payload:
        return None, None
    entry = payload[0] if isinstance(payload[0], dict) else {}
    meanings = entry.get("meanings") or []
    definition = None
    part_of_speech = None
    if meanings and isinstance(meanings[0], dict):
        part_of_speech = meanings[0].get("partOfSpeech")
        definitions = meanings[0].get("definitions") or []
        if definitions and isinstance(definitions[0], dict):
            definition = definitions[0].get("definition")
    if not definition:
        return None, None
    return definition, {"word": entry.get("word") or "", "phonetic": entry.get("phonetic") or "",
        "part_of_speech": part_of_speech or "", "definition": definition, "source": "Dictionary API"}


async def _dictionary_lookup(client: httpx.AsyncClient, query: str, lang: str) -> tuple[str | None, dict | None]:
    if len(query.split()) != 1 or not re.search(r"[a-z]", query):
        return None, None
    language = lang if lang in {"en", "fr", "de"} else "en"
    try:
        response = await client.get(
            f"https://api.dictionaryapi.dev/api/v2/entries/{language}/{quote(query, safe='')}"
        )
        if response.status_code != 200:
            return None, None
        return _dictionary_payload(response.json())
    except Exception as exc:
        print(f"Dictionary source failed: {exc}")
        return None, None


def _snippet(content: str | None, query: str, limit: int = 260) -> str:
    text = re.sub(r"\s+", " ", content or "").strip()
    if not text:
        return ""
    index = text.lower().find(query.lower()) if query else -1
    start = max(0, index - 70) if index >= 0 else 0
    return text[start:start + limit]


async def _crawler_lookup(db: AsyncSession, query: str) -> list[dict]:
    """Search crawler-indexed page text; this does not fetch arbitrary URLs."""
    tokens = list(dict.fromkeys(token for token in re.findall(r"[a-z0-9]{3,}", query.lower())[:6]))
    if not tokens:
        return []
    conditions = []
    for token in tokens:
        pattern = f"%{token}%"
        conditions.extend([CrawlerPage.title.ilike(pattern), CrawlerPage.content.ilike(pattern)])
    try:
        statement = (select(CrawlerPage).where(or_(*conditions)).order_by(
            case((CrawlerPage.title.ilike(f"%{query}%"), 0), else_=1),
            CrawlerPage.pagerank.desc(), CrawlerPage.last_crawled.desc()).limit(8))
        rows = (await db.execute(statement)).scalars().all()
        return [{"title": row.title or row.url, "url": row.url,
                 "snippet": _snippet(row.content, query), "pagerank": float(row.pagerank or 0.0),
                 "source": "LOMINII crawler"} for row in rows]
    except Exception as exc:
        await db.rollback()
        print(f"Crawler index lookup failed: {exc}")
        return []


async def _stored_news_lookup(db: AsyncSession, query: str, domain: str, intent: str) -> list[dict]:
    tokens = list(dict.fromkeys(token for token in re.findall(r"[a-z0-9]{3,}", query.lower())[:5]))
    try:
        if tokens:
            conditions = [NewsArticle.title.ilike(f"%{token}%") for token in tokens]
            rows = (await db.execute(select(NewsArticle).where(or_(*conditions))
                .order_by(NewsArticle.published_at.desc()).limit(6))).scalars().all()
            if rows:
                return [{"title": row.title, "url": row.url, "source": row.source or "LOMINII news index",
                    "published_at": row.published_at.isoformat() if row.published_at else None}
                    for row in rows if row.title and row.url]
        is_news = domain == "news" or "news" in (intent or "").lower() or "current" in (intent or "").lower()
        if is_news:
            categories = list(dict.fromkeys([domain, "general"]))
            cached = (await db.execute(select(NewsCache).where(NewsCache.category.in_(categories))
                .order_by(NewsCache.cached_at.desc()).limit(1))).scalar_one_or_none()
            if cached and isinstance(cached.articles, list):
                return [item for item in cached.articles[:6] if isinstance(item, dict)
                        and item.get("title") and item.get("url")]
    except Exception as exc:
        await db.rollback()
        print(f"Stored news lookup failed: {exc}")
    return []


@router.post("/")
async def unified_search(request: Request, email: str = Depends(get_search_identity),
                         db: AsyncSession = Depends(get_db)):
    data = await request.json()
    query = str(data.get("q", "")).strip()
    if not query:
        raise HTTPException(status_code=400, detail="Missing query")
    if is_blocked(query):
        raise HTTPException(status_code=400, detail="Blocked query")

    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    lang = (user.language if user and user.language else "en").lower().split("-", 1)[0]
    if lang not in {"en", "fr", "de"}:
        lang = "en"
    country = "Nigeria"
    tier = user.subscription_status if user else "free"
    norm_query = normalise(query, lang).strip()
    ctx = analyze(norm_query)
    domain = ctx.get("domain", "general")
    intent = str(ctx.get("intent") or "")
    cache_key = build_cache_key(norm_query, lang, domain)
    cached = (await db.execute(select(SearchCache).where(SearchCache.cache_key == cache_key))).scalar_one_or_none()
    ttl = CACHE_TTL_AUTHENTICATED if user else CACHE_TTL_ANONYMOUS
    if cached and cached.cached_at and (datetime.utcnow() - cached.cached_at.replace(tzinfo=None)) < timedelta(minutes=ttl):
        return cached.result

    # GSP values are independent of keyboard geometry except for c.
    uid_chain = calculate_uid_chain(norm_query, lang)
    L = calculate_lsum(norm_query, lang)
    S = calculate_ssum(norm_query, lang)
    c = first_letter_index(norm_query, lang)
    gsp = gsp_place(L, S, c, K=5)
    cloud = elastic_cloud(L, S, c, radius=1, first_letter_radius=1)
    primary = gsp["primary_cell"]

    gsg_data = None
    lat, lon = data.get("lat"), data.get("lon")
    if lat is not None and lon is not None:
        try:
            gsg_cell, _ = gps_to_gsg(float(lat), float(lon))
            gsg_data = {"grid_x": gsg_cell[0], "grid_y": gsg_cell[1],
                        "cell_id": f"city.{gsg_cell[0]}.{gsg_cell[1]}"}
        except Exception:
            gsg_data = None

    # Dictionary cache keys include language to avoid cross-language collisions.
    definition = None
    dictionary = None
    dictionary_cache_row = None
    dictionary_key = f"{lang}:{norm_query}"[:255]
    if len(norm_query.split()) == 1 and re.search(r"[a-z]", norm_query):
        try:
            dictionary_cache_row = (await db.execute(select(DictionaryCache)
                .where(DictionaryCache.word == dictionary_key))).scalar_one_or_none()
            if dictionary_cache_row and dictionary_cache_row.definition:
                definition = dictionary_cache_row.definition
                dictionary = {"word": norm_query, "definition": definition,
                               "source": "LOMINII dictionary cache"}
        except Exception as exc:
            await db.rollback()
            print(f"Dictionary cache lookup failed: {exc}")
            dictionary_cache_row = None

    crawler_results = await _crawler_lookup(db, norm_query)

    async def wiki_source():
        try:
            return await search_wikipedia(norm_query, lang=lang, limit=3)
        except Exception as exc:
            print(f"Wikipedia source failed: {exc}")
            return []

    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=3.0), follow_redirects=False) as client:
        jobs = {"wikipedia": wiki_source(), "web": _scrapingbee_search(client, norm_query),
                "news": _gnews_search(client, norm_query, lang)}
        if dictionary is None:
            jobs["dictionary"] = _dictionary_lookup(client, norm_query, lang)
        names = list(jobs)
        values = await asyncio.gather(*(jobs[name] for name in names), return_exceptions=True)
    sources = dict(zip(names, values))
    wiki_articles = sources.get("wikipedia", [])
    if not isinstance(wiki_articles, list): wiki_articles = []
    web_results = sources.get("web", [])
    if not isinstance(web_results, list): web_results = []
    news_articles = sources.get("news", [])
    if not isinstance(news_articles, list): news_articles = []

    if dictionary is None:
        dictionary_result = sources.get("dictionary")
        if isinstance(dictionary_result, tuple) and len(dictionary_result) == 2:
            definition, dictionary = dictionary_result
            if definition and dictionary:
                try:
                    if dictionary_cache_row:
                        dictionary_cache_row.definition = definition
                        dictionary_cache_row.language = lang
                        dictionary_cache_row.cached_at = datetime.utcnow()
                    else:
                        db.add(DictionaryCache(word=dictionary_key, definition=definition,
                            language=lang, cached_at=datetime.utcnow()))
                except Exception as exc:
                    print(f"Dictionary cache update failed: {exc}")

    if not news_articles:
        news_articles = await _stored_news_lookup(db, norm_query, domain, intent)

    ai_summary = None
    if not is_ai_blocked(query):
        source_text = (f"Dictionary: {definition or 'None'}\nNews: {news_articles}\n"
                       f"Wikipedia: {wiki_articles}\nWeb results: {web_results}\n"
                       f"Crawler index: {crawler_results}")
        try:
            prompt = build_prompt(query=norm_query, sources=source_text, country=country,
                language=lang, tier=tier, workspace="search", intent=intent)
            ai_summary = await generate(prompt, intent=intent, workspace="search",
                                        user_id=str(user.id) if user else None)
        except Exception as exc:
            print(f"Search AI summary failed: {exc}")
            ai_summary = None

    correction = (await db.execute(select(Correction).where(Correction.misspelled.ilike(norm_query))
        .order_by(Correction.confidence.desc()).limit(1))).scalar_one_or_none()
    did_you_mean = None
    if correction and correction.corrected.strip().lower() != norm_query.lower():
        did_you_mean = correction.corrected.strip()

    response = {
        "query": query, "L": L, "Lsum": L, "uID": uid_chain, "S": S, "Ssum": S, "c": c,
        "primary_cell_col": primary["col"], "primary_cell_row": primary["row"],
        "gsp": gsp, "elastic_cloud": cloud, "elastic_cloud_size": len(cloud),
        "definition": definition, "dictionary": dictionary, "news": news_articles,
        "wikipedia": wiki_articles, "web_results": web_results, "crawler_results": crawler_results,
        "ai_summary": ai_summary, "did_you_mean": did_you_mean, "related_questions": [],
        "gsg_cell": gsg_data,
        "source_status": {"dictionary": bool(definition), "news": bool(news_articles),
            "wikipedia": bool(wiki_articles), "web": bool(web_results), "crawler": bool(crawler_results)},
    }
    if user:
        db.add(Search(user_id=user.id, query=query, gsp_cell=f"{primary['col']},{primary['row']}"))
    if cached:
        cached.result = response
        cached.cached_at = datetime.utcnow()
    else:
        db.add(SearchCache(cache_key=cache_key, result=response, cached_at=datetime.utcnow()))
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return response
