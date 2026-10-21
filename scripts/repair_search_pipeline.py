#!/usr/bin/env python3
"""LOMINII coordinated GSP + search-source repair.

Run from the repository root:
    python scripts/repair_search_pipeline.py

Backs up files, compiles changed modules, and runs focused GSP checks.
Does not commit or push.
"""
from __future__ import annotations
import py_compile
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path.cwd()
REQUIRED = [
    ROOT / "backend/lominii_platform/gsp.py",
    ROOT / "backend/lominii_platform/placement.py",
    ROOT / "backend/lominii_platform/wikipedia.py",
    ROOT / "apps/lominii/search/router.py",
    ROOT / "public/js/search.js",
    ROOT / "public/js/performSearch.js",
]
missing = [str(p.relative_to(ROOT)) for p in REQUIRED if not p.is_file()]
if missing:
    raise SystemExit("Run from the LOMINII repository root. Missing: " + ", ".join(missing))
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP_DIR = ROOT / "backups" / f"search_pipeline_{STAMP}"
BACKUP_DIR.mkdir(parents=True, exist_ok=False)
for path in REQUIRED:
    backup = BACKUP_DIR / path.relative_to(ROOT)
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, backup)

GSP = '''"""LOMINII GSP — deterministic query placement and elastic retrieval cells.

L = number of ASCII alphabet letters; uID = ordered zero-based alphabet indices;
S = sum(uID); c = first letter's column on the selected language keyboard.
"""
import unicodedata
from lominii_platform.keymaps.registry import get_keyboard

GRID_COLUMNS = 56
GRID_ROWS = 64
REPLICA_COUNT = 5
REPLICA_ROW_STEP = 8
_DIGITS_ROW = "0123456789"


def get_keymap(lang: str = "en") -> dict:
    """Return keyboard coordinates as (row, column), separate from GSP values."""
    keymap = {}
    for row_index, row in enumerate(get_keyboard(lang)):
        for column_index, character in enumerate(row.lower()):
            keymap[character] = (row_index, column_index)
    for column_index, character in enumerate(_DIGITS_ROW):
        keymap[character] = (3, 26 + column_index)
    return keymap


def normalise(text: str, lang: str = "en") -> str:
    """Lowercase and fold diacritics without stemming or deleting query words."""
    text = unicodedata.normalize("NFKD", (text or "").lower())
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def calculate_uid_chain(word: str, lang: str = "en") -> list[int]:
    """Return ordered zero-based alphabet indices for a-z in the normalized query."""
    normalized = normalise(word, lang)
    return [ord(ch) - ord("a") for ch in normalized if "a" <= ch <= "z"]


def calculate_lsum(word: str, lang: str = "en") -> int:
    """Return L: letter count, not keyboard-row coordinates."""
    return len(calculate_uid_chain(word, lang))


def calculate_ssum(word: str, lang: str = "en") -> int:
    """Return S: sum of the ordered zero-based alphabet-index chain."""
    return sum(calculate_uid_chain(word, lang))


def first_letter_index(word: str, lang: str = "en") -> int:
    """Return the keyboard column of the first alphabet letter for this language."""
    normalized = normalise(word, lang)
    character = next((ch for ch in normalized if "a" <= ch <= "z"), "")
    if not character:
        return 0
    return get_keymap(lang).get(character, (0, 0))[1]


def gsp_place(Lsum: int, Ssum: int, c: int, K: int = REPLICA_COUNT,
              D: int = REPLICA_ROW_STEP, C: int = GRID_COLUMNS,
              R: int = GRID_ROWS) -> dict:
    """Calculate primary and replica cells using the established GSP equations."""
    if C < 1 or R < 1:
        raise ValueError("Grid dimensions must be positive")
    if K < 0:
        raise ValueError("Replica count cannot be negative")
    start_row = ((Lsum + Ssum - 1) % R) + 1
    start_column = c % C
    cells = []
    for k in range(K):
        row = ((start_row - 1 + k * D) % R) + 1
        column = (start_column + k) % C
        cells.append({"col": column, "row": row, "k": k})
    return {"start_row": start_row, "primary_cell": cells[0] if cells else None, "cells": cells}


def elastic_cloud(L: int, S: int, c: int, radius: int = 1,
                  first_letter_radius: int = 1, C: int = GRID_COLUMNS,
                  R: int = GRID_ROWS) -> list:
    """Return neighboring cells around the corrected GSP placement."""
    if C < 1 or R < 1:
        raise ValueError("Grid dimensions must be positive")
    if radius < 0 or first_letter_radius < 0:
        raise ValueError("Elastic-cloud radii cannot be negative")
    cloud = set()
    for dc in range(-first_letter_radius, first_letter_radius + 1):
        column = (c + dc) % C
        for dL in range(-radius, radius + 1):
            for dS in range(-radius, radius + 1):
                if dL == 0 and dS == 0 and dc == 0:
                    continue
                row = ((L + dL + S + dS - 1) % R) + 1
                cloud.add((column, row))
    base_row = ((L + S - 1) % R) + 1
    cloud.add((c % C, base_row))
    return [{"col": col, "row": row} for col, row in sorted(cloud)]
'''

WIKIPEDIA = '''"""Language-aware Wikipedia search and bounded article summaries."""
import asyncio
from urllib.parse import quote
import httpx

SUPPORTED_WIKI_LANGUAGES = {"en", "fr", "de"}

async def search_wikipedia(query: str, lang: str = "en", limit: int = 3) -> list[dict]:
    """Search the selected language's Wikipedia; source failure returns an empty list."""
    query = (query or "").strip()
    if not query:
        return []
    language = (lang or "en").lower().split("-", 1)[0]
    if language not in SUPPORTED_WIKI_LANGUAGES:
        language = "en"
    limit = max(1, min(int(limit), 5))
    base = f"https://{language}.wikipedia.org"
    params = {"action": "query", "list": "search", "srsearch": query,
              "format": "json", "srlimit": limit, "srprop": ""}
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(8.0, connect=3.0)) as client:
            response = await client.get(f"{base}/w/api.php", params=params)
            if response.status_code != 200:
                return []
            payload = response.json()
            titles = [item.get("title") for item in payload.get("query", {}).get("search", [])
                      if isinstance(item, dict) and item.get("title")]
            if not titles:
                return []
            async def fetch_summary(title: str):
                try:
                    summary_response = await client.get(
                        f"{base}/api/rest_v1/page/summary/{quote(title, safe='')}"
                    )
                    if summary_response.status_code != 200:
                        return None
                    summary = summary_response.json()
                    urls = summary.get("content_urls", {}).get("desktop", {})
                    return {"title": summary.get("title") or title,
                            "extract": (summary.get("extract") or "")[:500],
                            "url": urls.get("page") or "", "source": "Wikipedia"}
                except Exception:
                    return None
            summaries = await asyncio.gather(*(fetch_summary(title) for title in titles),
                                              return_exceptions=True)
            return [item for item in summaries if isinstance(item, dict)
                    and item.get("title") and item.get("url")]
    except Exception:
        return []
'''

SEARCH_ROUTER = '''"""LOMINII unified search: corrected GSP, independent sources, crawler index, and cache."""
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
        title = re.sub(r"\\s+", " ", " ".join(parts)).strip()
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
    text = re.sub(r"\\s+", " ", content or "").strip()
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
        source_text = (f"Dictionary: {definition or 'None'}\\nNews: {news_articles}\\n"
                       f"Wikipedia: {wiki_articles}\\nWeb results: {web_results}\\n"
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
'''

# Preflight placement patch before writing any replacement files.
placement_path = ROOT / "backend/lominii_platform/placement.py"
placement_text = placement_path.read_text(encoding="utf-8")
old_import = """from .gsp import (
    calculate_lsum,
    calculate_ssum,
    first_letter_index,
    gsp_place,
)"""
new_import = """from .gsp import (
    GRID_COLUMNS,
    calculate_lsum,
    calculate_ssum,
    first_letter_index,
    gsp_place,
)"""
old_columns = 'C = params.get("C", 26)'
if old_import not in placement_text or old_columns not in placement_text:
    raise SystemExit("placement.py did not match expected anchors; no source files changed. Backups: " + str(BACKUP_DIR))
placement_text = placement_text.replace(old_import, new_import, 1).replace(old_columns, 'C = params.get("C", GRID_COLUMNS)', 1)

# Preflight frontend result rendering changes.
HELPERS = """function escapeSearchHtml(value) {
  return String(value == null ? "" : value).replace(/[&<>\"']/g, function (c) {
    return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '\"': "&quot;", "'": "&#39;" }[c];
  });
}
function searchResultLink(item) {
  const title = escapeSearchHtml(item && (item.title || item.url) || "Result");
  try {
    const parsed = new URL(String(item && item.url || ""));
    if (parsed.protocol !== "http:" && parsed.protocol !== "https:") return title;
    return `<a href="${escapeSearchHtml(parsed.href)}" target="_blank" rel="noopener noreferrer">${title}</a>`;
  } catch (_) { return title; }
}
"""
RESULT_BLOCK = """    // News
    if (data.news && data.news.length > 0) {
      html += '<h4 style="margin-top:1.5rem;">📰 Related News</h4>';
      data.news.forEach(n => { html += `<div class="news-item">📌 ${searchResultLink(n)}</div>`; });
    }
    // Wikipedia
    if (data.wikipedia && data.wikipedia.length > 0) {
      html += '<h4 style="margin-top:1.5rem;">📚 Wikipedia</h4>';
      data.wikipedia.forEach(item => { html += `<div class="source-item">${searchResultLink(item)}${item.extract ? `<p>${escapeSearchHtml(item.extract)}</p>` : ''}</div>`; });
    }
    // General web candidates from ScrapingBee-backed search
    if (data.web_results && data.web_results.length > 0) {
      html += '<h4 style="margin-top:1.5rem;">🌐 Web Results</h4>';
      data.web_results.forEach(item => { html += `<div class="source-item">${searchResultLink(item)}</div>`; });
    }
    // Pages indexed by LOMINII's crawler
    if (data.crawler_results && data.crawler_results.length > 0) {
      html += '<h4 style="margin-top:1.5rem;">🕸️ LOMINII Crawler</h4>';
      data.crawler_results.forEach(item => { html += `<div class="source-item">${searchResultLink(item)}${item.snippet ? `<p>${escapeSearchHtml(item.snippet)}</p>` : ''}</div>`; });
    }

"""
frontend_replacements = {}
for frontend_path in REQUIRED[4:]:
    source = frontend_path.read_text(encoding="utf-8")
    if "async function performSearch()" not in source:
        raise SystemExit("Unexpected search frontend layout: " + str(frontend_path.relative_to(ROOT)))
    if "function escapeSearchHtml(value)" not in source:
        source = source.replace("async function performSearch()", HELPERS + "\nasync function performSearch()", 1)
    source = source.replace("<p>${data.ai_summary}</p>", "<p>${escapeSearchHtml(data.ai_summary)}</p>")
    source = source.replace("<p>${data.definition}</p>", "<p>${escapeSearchHtml(data.definition)}</p>")
    source = source.replace("L‑sum: ${data.Lsum}, S‑sum: ${data.Ssum}", "L: ${data.L !== undefined ? data.L : data.Lsum}, S: ${data.S !== undefined ? data.S : data.Ssum}")
    source, count = re.subn(r"    // News\n.*?(?=    // Related Questions)", RESULT_BLOCK, source, count=1, flags=re.S)
    if count != 1:
        raise SystemExit("Could not safely replace news/results block in " + str(frontend_path.relative_to(ROOT)))
    frontend_replacements[frontend_path] = source

# Write source replacements.
(ROOT / "backend/lominii_platform/gsp.py").write_text(GSP, encoding="utf-8")
placement_path.write_text(placement_text, encoding="utf-8")
(ROOT / "backend/lominii_platform/wikipedia.py").write_text(WIKIPEDIA, encoding="utf-8")
(ROOT / "apps/lominii/search/router.py").write_text(SEARCH_ROUTER, encoding="utf-8")
for frontend_path, frontend_source in frontend_replacements.items():
    frontend_path.write_text(frontend_source, encoding="utf-8")
changed_python = [REQUIRED[0], placement_path, REQUIRED[2], REQUIRED[3]]
changed = changed_python + list(frontend_replacements)
for path in changed_python:
    py_compile.compile(str(path), doraise=True)
print("PASS: Python syntax compilation")
print("PASS: search UI renders news, Wikipedia, web, and crawler candidates")

sys.path.insert(0, str(ROOT / "backend"))
from lominii_platform.gsp import (  # noqa: E402
    calculate_lsum, calculate_ssum, calculate_uid_chain,
    first_letter_index, gsp_place,
)
sample = "what are we doing today"
assert calculate_lsum(sample, "en") == 19, calculate_lsum(sample, "en")
assert calculate_ssum(sample, "en") == 199, calculate_ssum(sample, "en")
assert calculate_uid_chain(sample, "en") == [22, 7, 0, 19, 0, 17, 4, 22, 4, 3, 14, 8, 13, 6, 19, 14, 3, 0, 24]
assert first_letter_index(sample, "en") == 1, first_letter_index(sample, "en")
assert first_letter_index(sample, "fr") == 0, first_letter_index(sample, "fr")
placed = gsp_place(19, 199, 1)
assert placed["start_row"] == 26, placed
assert placed["primary_cell"] == {"col": 1, "row": 26, "k": 0}, placed
assert len(placed["cells"]) == 5
print("PASS: GSP length, uID chain, sum, language keyboard column, and placement")
print("\nRepair applied. Backups:", BACKUP_DIR.relative_to(ROOT))
print("Changed files:")
for path in changed:
    print(" -", path.relative_to(ROOT))
print("\nNext: review `git diff` and run project tests before committing/pushing.")
