from sqlalchemy import delete, func
"""LOMINII unified search: corrected GSP, independent sources, crawler index, and cache."""
import asyncio
import hashlib
import html
import httpx
import os
import re
import time
from collections import deque
from datetime import datetime, timedelta
from html.parser import HTMLParser
from urllib.parse import parse_qs, quote, urlencode, urlparse
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import case, or_, select, text, tuple_
from sqlalchemy.ext.asyncio import AsyncSession
from lominii_platform.gsp import (calculate_lsum, calculate_ssum, calculate_uid_chain,
    elastic_cloud, first_letter_index, keyboard_column_index, gsp_place, normalise,
    place_text, query_marker)
from lominii_platform.ai.prompt_builder import build_prompt
from lominii_platform.content_filter import is_blocked, is_ai_blocked
from lominii_platform.auth import oauth2_scheme, validate_token
from lominii_platform.database import get_db
from lominii_platform.gsg import gps_to_gsg
from lominii_platform.intent_analyzer import analyze
from lominii_platform.ai.gateway import generate
from lominii_platform.wikipedia import search_wikipedia
from lominii_platform.models.public import User
from lominii_platform.models.search import Search, Correction, NewsArticle, NewsCache, DictionaryCache, DictionaryGridEntry, DictionaryGridSnapshot, DictionaryLexicalToken, DictionaryLetterIndex, SearchCache
from lominii_platform.models.crawler import CrawlerPage, CrawlerWebsiteToken, CrawlerWebsiteCharacter
from lominii_platform.http_fetch import fetch_public_page
from lominii_platform.keymaps.keyboard import (detect_by_alphabet, detect_language,
    SUPPORTED_LANGUAGES, get_alphabet, grid_columns, tokenize, word_kind)

router = APIRouter(prefix="/api/search", tags=["Search"])
GNEWS_API_KEY = os.getenv("GNEWS_API_KEY", "").strip()
SCRAPINGBEE_API_KEY = os.getenv("SCRAPINGBEE_API_KEY", "").strip()
CACHE_TTL_ANONYMOUS = 5
CACHE_TTL_AUTHENTICATED = 300
CACHE_VERSION = "search-gsp-v6-alphabet-grid-numbers"


def _cell_label(marker: dict, col: int) -> str:
    """Readable column label: the language's own letter, or the digit on the number face."""
    face = marker.get("face", "L")
    if face == "N":
        return str(col)
    if face == "L":
        alphabet = get_alphabet(marker.get("lang", "en"))
        if 0 <= col < len(alphabet):
            return alphabet[col].upper()
    return "-"


def _cell_key(placement: dict) -> str:
    """"col,row" for letter faces; "N:col,row" for the number face, "X:..." if unplaceable."""
    primary = placement["primary_cell"]
    face = (placement.get("marker") or {}).get("face", "L")
    prefix = "" if face == "L" else f"{face}:"
    return f"{prefix}{primary['col']},{primary['row']}"

async def get_search_identity(token: str = Depends(oauth2_scheme)) -> str:
    """Accept valid guest tokens for free search, not other protected routes."""
    payload = validate_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    identity = payload.get("sub")
    if not isinstance(identity, str) or not identity:
        raise HTTPException(status_code=401, detail="Invalid token identity")
    return identity


# ---- search hardening ------------------------------------------------------
MAX_QUERY_CHARS = int(os.getenv("SEARCH_MAX_QUERY_CHARS", "300"))
SEARCH_RATE_PER_MINUTE = int(os.getenv("SEARCH_RATE_PER_MINUTE", "30"))
_rate_hits: dict[str, deque] = {}


def _rate_limited(key: str, limit: int | None = None, window: float = 60.0) -> int:
    """0 if allowed, else seconds to wait. In-process sliding window (per worker)."""
    limit = SEARCH_RATE_PER_MINUTE if limit is None else limit
    if limit <= 0:
        return 0
    now = time.monotonic()
    hits = _rate_hits.setdefault(key, deque())
    while hits and now - hits[0] > window:
        hits.popleft()
    if len(hits) >= limit:
        return max(1, int(window - (now - hits[0])) + 1)
    hits.append(now)
    if len(_rate_hits) > 10000:  # drop idle keys so the table cannot grow forever
        for stale in [k for k, v in _rate_hits.items() if not v or now - v[-1] > window]:
            _rate_hits.pop(stale, None)
    return 0


def _like_escape(value: str) -> str:
    """Escape LIKE wildcards so user text is matched literally."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _gsg_for_request(data: dict) -> dict | None:
    """GSG cell for THIS request only; never taken from a shared cache."""
    lat, lon = data.get("lat"), data.get("lon")
    if lat is None or lon is None:
        return None
    try:
        lat, lon = float(lat), float(lon)
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            return None
        gsg_cell, _ = gps_to_gsg(lat, lon)
        return {"grid_x": gsg_cell[0], "grid_y": gsg_cell[1],
                "cell_id": f"city.{gsg_cell[0]}.{gsg_cell[1]}"}
    except Exception:
        return None


def _edit_distance(a: str, b: str, cap: int = 3) -> int:
    """Insert/delete/replace/swap distance; returns cap + 1 when above cap."""
    if abs(len(a) - len(b)) > cap:
        return cap + 1
    prev2 = None
    prev = list(range(len(b) + 1))
    for i in range(1, len(a) + 1):
        cur = [i] + [0] * len(b)
        for j in range(1, len(b) + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                cur[j] = min(cur[j], prev2[j - 2] + 1)
        if min(cur) > cap:
            return cap + 1
        prev2, prev = prev, cur
    return prev[-1]


def _rank_suggestions(query: str, candidates, limit: int = 5) -> list[str]:
    """candidates: (display_word, normalized_word) pairs, most recently used first.
    Nearest edit distance wins; ties keep the incoming (recency) order."""
    max_dist = 1 if len(query) <= 4 else 2
    seen, scored = set(), []
    for display, normalized in candidates:
        normalized = (normalized or "").strip()
        if not normalized or normalized == query or normalized in seen:
            continue
        distance = _edit_distance(query, normalized, cap=max_dist)
        if distance <= max_dist:
            seen.add(normalized)
            scored.append((distance, abs(len(normalized) - len(query)),
                           normalized, display or normalized))
    scored.sort(key=lambda item: item[0])  # stable: ties keep the recency order
    return [item[3] for item in scored[:limit]]


async def _cloud_suggestions(db, norm_query: str, lang: str, cloud: list, limit: int = 5) -> list[str]:
    """Near-miss words found in the elastic cloud's neighbouring grid cells."""
    if len(norm_query) < 3 or not cloud:
        return []
    cells = [(item["col"], item["row"]) for item in cloud][:40]
    try:
        rows = (await db.execute(
            select(DictionaryGridEntry.word, DictionaryGridEntry.normalized_word)
            .where(
                DictionaryGridEntry.language == lang,
                tuple_(DictionaryGridEntry.primary_cell_col,
                       DictionaryGridEntry.primary_cell_row).in_(cells),
            )
            .order_by(DictionaryGridEntry.last_seen_at.desc().nullslast())
            .limit(400)
        )).all()
    except Exception as exc:
        await db.rollback()
        print(f"Cloud suggestions failed: {exc}")
        return []
    return _rank_suggestions(norm_query, [(row[0], row[1]) for row in rows], limit)


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


async def _dictionary_grid_lookup(db, query, lang, uid_chain):
    """Look up a word in the persistent lexicon before external APIs."""
    normalized = normalise(query, lang).strip()
    if not normalized or not uid_chain:
        return None, None, None
    try:
        result = await db.execute(
            select(DictionaryGridEntry).where(
                DictionaryGridEntry.language == lang,
                DictionaryGridEntry.normalized_word == normalized,
            ).limit(1)
        )
        entry = result.scalar_one_or_none()
        if entry is None:
            result = await db.execute(
                select(DictionaryGridEntry).where(
                    DictionaryGridEntry.language == lang,
                    DictionaryGridEntry.uid_chain == uid_chain,
                ).limit(8)
            )
            candidates = result.scalars().all()
            entry = next(
                (item for item in candidates
                 if normalise(item.word, lang).strip() == normalized),
                None,
            )
        if entry is None or not entry.definition:
            return None, None, None
        return entry.definition, {
            "word": entry.word,
            "phonetic": entry.phonetic or "",
            "part_of_speech": entry.part_of_speech or "",
            "definition": entry.definition,
            "source": entry.source or "LOMINII Lexicon",
        }, entry
    except Exception as exc:
        print(f"Local dictionary index lookup failed: {exc}")
        return None, None, None


async def _dictionary_lookup(client: httpx.AsyncClient, query: str, lang: str) -> tuple[str | None, dict | None]:
    if len(query.split()) != 1 or not any(ch.isalpha() for ch in query):
        return None, None
    language = lang if lang in {"en", "fr", "de"} else None
    if language is None:
        return None, None
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



def _website_token_records(url_hash: str, text: str, language: str, section: str):
    """Extract normalized token occurrences and their character positions."""
    records = []
    character_records = []

    for position, match in enumerate(
        re.finditer(r"[^\W_]+(?:['’\-][^\W_]+)*", text or "", flags=re.UNICODE)
    ):
        original = match.group(0)
        normalized = normalise(original, language).strip().lower()

        if not normalized or len(normalized) > 255:
            continue

        records.append({
            "url_hash": url_hash,
            "normalized_token": normalized,
            "original_token": original,
            "language": (language or "en")[:16],
            "section": section,
            "token_position": position,
            "char_start": match.start(),
            "kind": word_kind(normalized, language or "en"),
        })

        # One row per tokenizer unit: a digraph letter ("gb", "sh") is one row,
        # digits are marked N so they are never read as letters, and letters
        # outside the alphabet are marked F instead of being dropped.
        for char_position, unit in enumerate(tokenize(normalized, language or "en")):
            character_records.append({
                "url_hash": url_hash,
                "character": unit.value[:8],
                "kind": unit.kind,
                "character_position": char_position,
                "normalized_token": normalized,
                "language": (language or "en")[:16],
                "section": section,
                "token_position": position,
            })

    return records, character_records


async def _rebuild_website_lexical_index(
    db: AsyncSession,
    url_hash: str,
    title: str,
    content: str,
    language: str,
) -> None:
    """Replace lexical records for one fetched page."""
    await db.execute(
        delete(CrawlerWebsiteToken).where(
            CrawlerWebsiteToken.url_hash == url_hash
        )
    )
    await db.execute(
        delete(CrawlerWebsiteCharacter).where(
            CrawlerWebsiteCharacter.url_hash == url_hash
        )
    )

    token_rows = []
    character_rows = []

    for section, text in (
        ("title", title or ""),
        ("body", content or ""),
    ):
        tokens, characters = _website_token_records(
            url_hash, text, language or "en", section
        )
        token_rows.extend(tokens)
        character_rows.extend(characters)

    # Bound per-page indexing work to avoid pathological page payloads.
    token_rows = token_rows[:50000]
    character_rows = character_rows[:250000]

    if token_rows:
        await db.execute(CrawlerWebsiteToken.__table__.insert(), token_rows)

    if character_rows:
        await db.execute(
            CrawlerWebsiteCharacter.__table__.insert(),
            character_rows,
        )


async def _crawler_lookup(db: AsyncSession, query: str, lang: str = 'en') -> list[dict]:
    """Retrieve crawler pages using indexed lexical tokens, then fallback."""
    tokens = list(dict.fromkeys(
        token for token in re.findall(r"[^\W_]+", query.lower(), flags=re.UNICODE)
        if len(token) >= 2 or word_kind(token, lang or "en") == "N"
    ))[:10]

    if not tokens:
        return []

    try:
        # First pass: exact normalized-token matches in fetched website text.
        normalized_tokens = []
        for token in tokens:
            try:
                normalized_tokens.append(normalise(token, lang or "en").strip().lower())
            except Exception:
                normalized_tokens.append(token)

        normalized_tokens = list(dict.fromkeys(t for t in normalized_tokens if t))

        matched = []
        if normalized_tokens:
            token_statement = (
                select(
                    CrawlerWebsiteToken.url_hash,
                    func.count(
                        func.distinct(CrawlerWebsiteToken.normalized_token)
                    ).label("matched_tokens"),
                )
                .where(
                    CrawlerWebsiteToken.normalized_token.in_(normalized_tokens)
                )
                .group_by(CrawlerWebsiteToken.url_hash)
                .order_by(func.count(
                    func.distinct(CrawlerWebsiteToken.normalized_token)
                ).desc())
                .limit(30)
            )
            matched = (await db.execute(token_statement)).all()

        results = []
        if matched:
            scores = {row.url_hash: int(row.matched_tokens or 0) for row in matched}
            pages = (
                await db.execute(
                    select(CrawlerPage).where(
                        CrawlerPage.url_hash.in_(list(scores.keys()))
                    )
                )
            ).scalars().all()

            # GSP-aware ranking: cell agreement is a relevance signal,
            # not a hard filter that can hide otherwise relevant pages.
            query_cell = None
            try:
                normalized_query = normalise(query, lang or "en")
                resolved = place_text(normalized_query, lang or "en", K=5)
                primary = resolved.get("primary_cell") or {}
                if "col" in primary and "row" in primary:
                    query_cell = _cell_key(resolved)
            except Exception as exc:
                print(f"GSP query resolution unavailable: {exc}")

            query_lower = query.casefold()
            query_terms = set(normalized_tokens)
            query_phrase = " ".join(query_lower.split())

            def page_relevance(page):
                title = (page.title or "").casefold()
                content = (page.content or "").casefold()
                page_cell = (page.gsp_cell or "").strip()

                title_hits = sum(
                    1 for term in query_terms if term and term in title
                )
                phrase_title = int(
                    bool(query_phrase and query_phrase in title)
                )
                phrase_body = int(
                    bool(query_phrase and query_phrase in content)
                )
                gsp_match = int(
                    bool(query_cell and page_cell == query_cell)
                )

                return (
                    phrase_title,
                    gsp_match,
                    scores.get(page.url_hash, 0),
                    title_hits,
                    phrase_body,
                    float(page.pagerank or 0.0),
                    page.last_crawled.timestamp()
                    if page.last_crawled else 0.0,
                )

            pages.sort(key=page_relevance, reverse=True)

            for page in pages[:8]:
                results.append({
                    "title": page.title or page.url,
                    "url": page.url,
                    "snippet": _snippet(page.content, query),
                    "pagerank": float(page.pagerank or 0.0),
                    "source": "LOMINII crawler",
                })

        if results:
            return results

        # Compatibility fallback for older pages not yet lexically indexed.
        conditions = []
        for token in tokens[:6]:
            pattern = f"%{token}%"
            conditions.append(CrawlerPage.title.ilike(pattern))
            # Trigram indexes cover 3+ characters; shorter tokens would scan every page.
            if len(token) >= 3:
                conditions.append(CrawlerPage.content.ilike(pattern))

        statement = (
            select(CrawlerPage)
            .where(or_(*conditions))
            .order_by(
                case(
                    (CrawlerPage.title.ilike(f"%{_like_escape(query)}%", escape="\\"), 0),
                    else_=1,
                ),
                CrawlerPage.pagerank.desc(),
                CrawlerPage.last_crawled.desc(),
            )
            .limit(8)
        )
        # Never let the fallback scan run away; restore the default afterwards.
        await db.execute(text("SET LOCAL statement_timeout = 2500"))
        rows = (await db.execute(statement)).scalars().all()
        await db.execute(text("SET LOCAL statement_timeout = DEFAULT"))

        return [{
            "title": row.title or row.url,
            "url": row.url,
            "snippet": _snippet(row.content, query),
            "pagerank": float(row.pagerank or 0.0),
            "source": "LOMINII crawler",
        } for row in rows]

    except Exception as exc:
        await db.rollback()
        print(f"Crawler lexical lookup failed: {exc}")
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



async def _fetch_and_index_web_results(
    db: AsyncSession, results: list[dict], lang: str
) -> list[dict]:
    """
    Fetch a small number of discovered pages and persist them in the crawler
    index. Existing recently fetched pages are reused.
    """
    candidates = []
    seen_urls = set()

    for item in results[:3]:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or "").strip()
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        candidates.append(item)

    if not candidates:
        return []

    async def load_one(item):
        url = str(item.get("url") or "")
        try:
            from hashlib import sha256
            url_hash = sha256(url.encode("utf-8")).hexdigest()
            existing = (
                await db.execute(
                    select(CrawlerPage).where(CrawlerPage.url_hash == url_hash)
                )
            ).scalar_one_or_none()

            now = datetime.utcnow()
            if (
                existing
                and existing.content
                and existing.last_crawled
                and (now - existing.last_crawled.replace(tzinfo=None))
                    < timedelta(hours=24)
            ):
                return {
                    "title": existing.title or item.get("title") or url,
                    "url": existing.url,
                    "snippet": _snippet(existing.content, str(item.get("title") or ""), 260),
                    "source": "LOMINII crawler",
                }

            page = await fetch_public_page(url)
            if not page:
                return None

            normalized_title = normalise(page["title"], lang)
            cell = _cell_key(place_text(normalized_title, lang, K=5))

            if existing:
                existing.url = page["url"]
                existing.title = page["title"]
                existing.content = page["content"]
                existing.gsp_cell = cell
                existing.last_crawled = now
            else:
                db.add(CrawlerPage(
                    url_hash=url_hash,
                    url=page["url"],
                    title=page["title"],
                    content=page["content"],
                    gsp_cell=cell,
                    pagerank=0.0,
                    last_crawled=now,
                ))

            return {
                "title": page["title"],
                "url": page["url"],
                "snippet": _snippet(page["content"], str(item.get("title") or ""), 260),
                "source": "LOMINII HTTP fetch",
            }
        except Exception as exc:
            print(f"LOMINII page fetch/index failed: {exc}")
            return None

    # SQLAlchemy AsyncSession is not safe for concurrent operations. Fetch
    # network content concurrently first, then persist rows sequentially.
    async def fetch_only(item):
        url = str(item.get("url") or "")
        page = await fetch_public_page(url)
        return item, page

    fetched = await asyncio.gather(
        *(fetch_only(item) for item in candidates),
        return_exceptions=True,
    )
    indexed = []

    for result in fetched:
        if isinstance(result, BaseException):
            continue
        item, page = result
        if not page:
            continue

        try:
            from hashlib import sha256
            url_hash = sha256(page["url"].encode("utf-8")).hexdigest()
            existing = (
                await db.execute(
                    select(CrawlerPage).where(CrawlerPage.url_hash == url_hash)
                )
            ).scalar_one_or_none()

            now = datetime.utcnow()
            title = page["title"]
            cell = _cell_key(place_text(normalise(title, lang), lang, K=5))

            if existing:
                existing.title = title
                existing.content = page["content"]
                existing.gsp_cell = cell
                existing.last_crawled = now
            else:
                db.add(CrawlerPage(
                    url_hash=url_hash,
                    url=page["url"],
                    title=title,
                    content=page["content"],
                    gsp_cell=cell,
                    pagerank=0.0,
                    last_crawled=now,
                ))

            await db.flush()
            await _rebuild_website_lexical_index(
                db=db,
                url_hash=url_hash,
                title=title,
                content=page.get("content") or "",
                language=lang or "en",
            )

            indexed.append({
                "title": title,
                "url": page["url"],
                "snippet": _snippet(page["content"], str(item.get("title") or ""), 260),
                "source": "LOMINII HTTP fetch",
            })
        except Exception as exc:
            print(f"LOMINII page persistence failed: {exc}")
            await db.rollback()

    return indexed



def _dictionary_lexical_records(word: str, definition: str, lang: str):
    """Build bounded token records from a complete headword and definition."""
    records = []
    seen = set()

    for token_type, text in (("word", word), ("meaning", definition)):
        position = 0

        for raw in re.findall(r"[^\W_]+(?:['’\-][^\W_]+)*", text, flags=re.UNICODE):
            original = raw.strip()
            normalized = normalise(original, lang).strip().lower()

            if not normalized or len(normalized) > 255:
                position += 1
                continue

            # Keep one token record for each distinct token/type combination.
            key = (token_type, normalized)
            if key not in seen:
                records.append({
                    "normalized_token": normalized,
                    "original_token": original[:255],
                    "token_type": token_type,
                    "token_position": position,
                    "kind": word_kind(normalized, lang),
                })
                seen.add(key)

            position += 1

            # Avoid unbounded database writes from pathological input.
            if len(records) >= 1500:
                break

        if len(records) >= 1500:
            break

    return records


async def _rebuild_dictionary_lexical_indexes(db, entry):
    """Replace an entry's token and character indexes after an upsert."""
    from sqlalchemy import delete

    await db.execute(
        delete(DictionaryLexicalToken).where(
            DictionaryLexicalToken.dictionary_entry_id == entry.id
        )
    )
    await db.execute(
        delete(DictionaryLetterIndex).where(
            DictionaryLetterIndex.dictionary_entry_id == entry.id
        )
    )

    tokens = _dictionary_lexical_records(
        entry.word, entry.definition, entry.language
    )

    for token in tokens:
        db.add(DictionaryLexicalToken(
            dictionary_entry_id=entry.id,
            language=entry.language,
            normalized_token=token["normalized_token"],
            original_token=token["original_token"],
            token_type=token["token_type"],
            token_position=token["token_position"],
            kind=token["kind"],
        ))

        for char_position, unit in enumerate(
            tokenize(token["normalized_token"], entry.language)
        ):
            db.add(DictionaryLetterIndex(
                dictionary_entry_id=entry.id,
                language=entry.language,
                normalized_token=token["normalized_token"],
                character=unit.value[:8],
                kind=unit.kind,
                character_position=char_position,
                token_type=token["token_type"],
            ))


async def _create_dictionary_grid_snapshots(db, checkpoint_size: int = 2000):
    """
    Create one timestamped snapshot for every newly crossed 2,000-entry
    boundary. Each snapshot contains the complete records for that checkpoint.
    """
    from sqlalchemy import func

    total = int(
        (await db.execute(
            select(func.count(DictionaryGridEntry.id))
        )).scalar_one() or 0
    )

    latest_snapshot = (
        await db.execute(
            select(DictionaryGridSnapshot)
            .order_by(DictionaryGridSnapshot.total_indexed.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    last_checkpoint = (
        int(latest_snapshot.total_indexed)
        if latest_snapshot is not None else 0
    )

    next_checkpoint = ((last_checkpoint // checkpoint_size) + 1) * checkpoint_size

    while next_checkpoint <= total:
        rows = (
            await db.execute(
                select(DictionaryGridEntry)
                .order_by(DictionaryGridEntry.id)
                .offset(next_checkpoint - checkpoint_size)
                .limit(checkpoint_size)
            )
        ).scalars().all()

        if len(rows) != checkpoint_size:
            # Do not create a misleading/incomplete checkpoint.
            break

        snapshot_entries = [
            {
                "id": row.id,
                "word": row.word,
                "normalized_word": row.normalized_word,
                "language": row.language,
                "definition": row.definition,
                "phonetic": row.phonetic,
                "part_of_speech": row.part_of_speech,
                "source": row.source,
                "source_url": row.source_url,
                "uid_chain": row.uid_chain or [],
                "L_sum": row.L_sum,
                "S_sum": row.S_sum,
                "keyboard_column": row.keyboard_column,
                "grid_columns": row.grid_columns or grid_columns(row.language),
                "primary_cell_col": row.primary_cell_col,
                "primary_cell_row": row.primary_cell_row,
                "replica_cells": row.replica_cells or [],
                "indexed_at": (
                    row.indexed_at.isoformat() if row.indexed_at else None
                ),
            }
            for row in rows
        ]

        db.add(DictionaryGridSnapshot(
            total_indexed=next_checkpoint,
            checkpoint_size=checkpoint_size,
            grid_columns=max(grid_columns(code) for code in SUPPORTED_LANGUAGES),
            grid_rows=64,
            entries=snapshot_entries,
            snapshot_at=datetime.utcnow(),
        ))

        await db.flush()
        next_checkpoint += checkpoint_size


@router.post("/dictionary/index")
async def index_dictionary_batch(
    request: Request,
    email: str = Depends(get_search_identity),
    db: AsyncSession = Depends(get_db),
):
    """Index dictionary entries, lexical tokens, letters, and grid snapshots."""
    actor = (
        await db.execute(
            select(User).where(User.email == email).limit(1)
        )
    ).scalar_one_or_none()

    if actor is None or str(actor.role or "").lower() != "admin":
        raise HTTPException(
            status_code=403,
            detail="Administrator access required",
        )

    data = await request.json()
    entries = data.get("entries")

    if not isinstance(entries, list) or not entries:
        raise HTTPException(
            status_code=400,
            detail="entries must be a non-empty list",
        )

    if len(entries) > 500:
        raise HTTPException(
            status_code=413,
            detail="Maximum 500 entries per batch",
        )

    requested_lang = str(data.get("language") or data.get("lang") or "en")
    lang = requested_lang.lower().split("-", 1)[0]

    if lang not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=400,
            detail="Unsupported language",
        )

    inserted = updated = skipped = 0
    indexed_ids = []

    try:
        for item in entries:
            if not isinstance(item, dict):
                skipped += 1
                continue

            word = str(item.get("word") or "").strip()
            definition = str(item.get("definition") or "").strip()

            if (
                not word
                or not definition
                or len(word) > 255
                or len(definition) > 12000
                or len(word.split()) != 1
                or not any(ch.isalpha() for ch in word)
            ):
                skipped += 1
                continue

            normalized = normalise(word, lang).strip()

            if not normalized or len(normalized) > 255:
                skipped += 1
                continue

            marker = query_marker(normalized, lang)
            chain = marker["uid"]
            L = marker["L"]
            S = marker["S"]

            # Main GSP column is the alphabet index; keyboard_column is physical.
            gsp_column = marker["c"]
            physical_keyboard_column = keyboard_column_index(normalized, lang)

            placement = gsp_place(
                L, S, gsp_column, K=5, C=marker["columns"], R=64
            )
            primary = placement.get("primary_cell") or {}

            if "col" not in primary or "row" not in primary:
                skipped += 1
                continue

            result = await db.execute(
                select(DictionaryGridEntry).where(
                    DictionaryGridEntry.language == lang,
                    DictionaryGridEntry.normalized_word == normalized,
                ).limit(1)
            )
            entry = result.scalar_one_or_none()
            now = datetime.utcnow()

            values = {
                "word": word,
                "normalized_word": normalized,
                "language": lang,
                "definition": definition,
                "phonetic": str(item.get("phonetic") or "")[:255],
                "part_of_speech": str(item.get("part_of_speech") or "")[:100],
                "source": str(item.get("source") or "LOMINII Lexicon")[:255],
                "source_url": str(item.get("source_url") or "")[:2000] or None,
                "uid_chain": chain,
                "L_sum": L,
                "S_sum": S,
                "keyboard_column": physical_keyboard_column,
                "grid_columns": marker["columns"],
                "primary_cell_col": primary["col"],
                "primary_cell_row": primary["row"],
                "replica_cells": [
                    {
                        "col": cell["col"],
                        "row": cell["row"],
                        "k": cell["k"],
                    }
                    for cell in (placement.get("cells") or [])
                ],
                "last_seen_at": now,
            }

            if entry is None:
                entry = DictionaryGridEntry(
                    **values,
                    indexed_at=now,
                )
                db.add(entry)
                inserted += 1
            else:
                for key, value in values.items():
                    setattr(entry, key, value)
                updated += 1

            # Ensure the entry has a database ID before creating child indexes.
            await db.flush()
            await _rebuild_dictionary_lexical_indexes(db, entry)
            indexed_ids.append(entry.id)

        # Checkpoint creation is based on total distinct grid entries,
        # not the number of rows received in this particular batch.
        await db.flush()
        await _create_dictionary_grid_snapshots(db, checkpoint_size=2000)
        await db.commit()

    except Exception as exc:
        await db.rollback()
        print(f"Dictionary batch indexing failed: {exc}")
        raise HTTPException(
            status_code=500,
            detail="Dictionary batch indexing failed",
        )

    return {
        "ok": True,
        "language": lang,
        "received": len(entries),
        "inserted": inserted,
        "updated": updated,
        "skipped": skipped,
        "lexical_entries_reindexed": len(indexed_ids),
        "snapshot_checkpoint_size": 2000,
    }

@router.post("/")
async def unified_search(request: Request, email: str = Depends(get_search_identity),
                         db: AsyncSession = Depends(get_db)):
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    if not isinstance(data, dict):
        raise HTTPException(status_code=400, detail="Invalid request body")
    raw_query = str(data.get("q", ""))
    query = " ".join("".join(ch for ch in raw_query if ch.isprintable() or ch.isspace()).split())
    if not query:
        raise HTTPException(status_code=400, detail="Missing query")
    if len(query) > MAX_QUERY_CHARS:
        raise HTTPException(status_code=400, detail=f"Query too long (max {MAX_QUERY_CHARS} characters)")
    if is_blocked(query):
        raise HTTPException(status_code=400, detail="Blocked query")

    wait = _rate_limited(f"search:{email}")
    if wait:
        raise HTTPException(status_code=429, detail="Too many searches. Please slow down.",
                            headers={"Retry-After": str(wait)})

    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    requested_lang = str(data.get("language") or data.get("lang") or "").lower().split("-", 1)[0]
    saved_lang = str(user.language or "").lower().split("-", 1)[0] if user and user.language else ""
    alphabet_lang = detect_by_alphabet(query)
    if requested_lang in SUPPORTED_LANGUAGES:
        lang = requested_lang
    elif alphabet_lang:
        lang = alphabet_lang
    elif saved_lang in SUPPORTED_LANGUAGES:
        lang = saved_lang
    else:
        lang = detect_language(query, default="en")
    country = user.country if user and getattr(user, "country", None) else "Nigeria"
    tier = user.subscription_status if user else "free"
    norm_query = normalise(query, lang).strip()
    ctx = analyze(norm_query)
    domain = ctx.get("domain", "general")
    intent = str(ctx.get("intent") or "")
    cache_key = build_cache_key(norm_query, lang, domain)
    cached = (await db.execute(select(SearchCache).where(SearchCache.cache_key == cache_key))).scalar_one_or_none()
    ttl = CACHE_TTL_AUTHENTICATED if user else CACHE_TTL_ANONYMOUS
    if cached and cached.cached_at and (datetime.utcnow() - cached.cached_at.replace(tzinfo=None)) < timedelta(minutes=ttl):
        # Per-request fields never come from another user's cached copy.
        hit = dict(cached.result)
        hit["query"] = query
        hit["gsg_cell"] = _gsg_for_request(data)
        if user:
            try:
                db.add(Search(user_id=user.id, query=query,
                              gsp_cell=_cell_key(place_text(norm_query, lang, K=5))))
                await db.commit()
            except Exception:
                await db.rollback()
        return hit

    # GSP values are independent of keyboard geometry except for c.
    marker = query_marker(norm_query, lang)
    uid_chain = marker["uid"]
    L, S, c = marker["L"], marker["S"], marker["c"]
    keyboard_c = keyboard_column_index(norm_query, lang)
    gsp = gsp_place(L, S, c, K=5, C=marker["columns"], R=64)
    gsp["marker"] = marker
    cloud = elastic_cloud(L, S, c, radius=1, first_letter_radius=1, C=marker["columns"])
    primary = gsp["primary_cell"]

    gsg_data = _gsg_for_request(data)

    # Dictionary lookup order: GSP-indexed grid, then legacy dictionary cache,
    # then the external dictionary API if no usable indexed record exists.
    definition = None
    dictionary = None
    dictionary_cache_row = None
    grid_entry = None
    dictionary_key = f"{lang}:{norm_query}"[:255]
    is_single_dictionary_term = (
        len(norm_query.split()) == 1 and any(ch.isalpha() for ch in norm_query)
    )

    if is_single_dictionary_term:
        try:
            grid_entry = (await db.execute(
                select(DictionaryGridEntry).where(
                    DictionaryGridEntry.language == lang,
                    DictionaryGridEntry.normalized_word == norm_query,
                    DictionaryGridEntry.primary_cell_col == primary["col"],
                    DictionaryGridEntry.primary_cell_row == primary["row"],
                ).limit(1)
            )).scalar_one_or_none()

            if grid_entry is None:
                _, _, grid_entry = await _dictionary_grid_lookup(
                    db, norm_query, lang, uid_chain
                )

            if grid_entry and grid_entry.definition:
                definition = grid_entry.definition
                dictionary = {
                    "word": grid_entry.word,
                    "definition": grid_entry.definition,
                    "phonetic": grid_entry.phonetic or "",
                    "part_of_speech": grid_entry.part_of_speech or "",
                    "source": grid_entry.source or "LOMINII dictionary grid",
                    "source_url": grid_entry.source_url,
                    "grid": {
                        "primary_cell_col": grid_entry.primary_cell_col,
                        "primary_cell_row": grid_entry.primary_cell_row,
                        "replica_cells": grid_entry.replica_cells or [],
                    },
                }
                grid_entry.last_seen_at = datetime.utcnow()
        except Exception as exc:
            await db.rollback()
            print(f"Dictionary grid lookup failed: {exc}")
            grid_entry = None

    if is_single_dictionary_term and dictionary is None:
        try:
            dictionary_cache_row = (await db.execute(
                select(DictionaryCache).where(
                    DictionaryCache.word == dictionary_key
                )
            )).scalar_one_or_none()

            if dictionary_cache_row and dictionary_cache_row.definition:
                definition = dictionary_cache_row.definition
                dictionary = {
                    "word": norm_query,
                    "definition": definition,
                    "source": "LOMINII dictionary cache",
                }
        except Exception as exc:
            await db.rollback()
            print(f"Dictionary cache lookup failed: {exc}")
            dictionary_cache_row = None

    crawler_results = await _crawler_lookup(db, norm_query, lang)

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
    fetched_pages = await _fetch_and_index_web_results(db, web_results, lang)
    if fetched_pages:
        crawler_results = (fetched_pages + crawler_results)[:12]
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

    # Persist successful external dictionary lookups in the GSP grid.
    # Grid placement is calculated by the same functions used for the query.
    if definition and dictionary and is_single_dictionary_term:
        try:
            if grid_entry is None:
                grid_entry = (await db.execute(
                    select(DictionaryGridEntry).where(
                        DictionaryGridEntry.language == lang,
                        DictionaryGridEntry.normalized_word == norm_query,
                    ).limit(1)
                )).scalar_one_or_none()

            entry_word = str(dictionary.get("word") or norm_query)[:255]
            source_url = (
                "https://api.dictionaryapi.dev/api/v2/entries/"
                f"{lang}/{quote(norm_query, safe='')}"
            )
            replica_cells = [
                {"col": cell["col"], "row": cell["row"], "k": cell["k"]}
                for cell in gsp["cells"]
            ]

            if grid_entry is None:
                grid_entry = DictionaryGridEntry(
                    language=lang,
                    normalized_word=norm_query[:255],
                    word=entry_word,
                    definition=definition,
                    phonetic=str(dictionary.get("phonetic") or "")[:255],
                    part_of_speech=str(dictionary.get("part_of_speech") or "")[:100],
                    source=str(dictionary.get("source") or "Dictionary API")[:255],
                    source_url=source_url,
                    uid_chain=uid_chain,
                    L_sum=L,
                    S_sum=S,
                    keyboard_column=keyboard_c,
                    grid_columns=marker["columns"],
                    primary_cell_col=primary["col"],
                    primary_cell_row=primary["row"],
                    replica_cells=replica_cells,
                    indexed_at=datetime.utcnow(),
                    last_seen_at=datetime.utcnow(),
                )
                db.add(grid_entry)
            else:
                grid_entry.word = entry_word
                grid_entry.definition = definition
                grid_entry.phonetic = str(dictionary.get("phonetic") or "")[:255]
                grid_entry.part_of_speech = str(
                    dictionary.get("part_of_speech") or ""
                )[:100]
                grid_entry.source = str(
                    dictionary.get("source") or "Dictionary API"
                )[:255]
                grid_entry.source_url = source_url
                grid_entry.uid_chain = uid_chain
                grid_entry.L_sum = L
                grid_entry.S_sum = S
                grid_entry.keyboard_column = keyboard_c
                grid_entry.grid_columns = marker["columns"]
                grid_entry.primary_cell_col = primary["col"]
                grid_entry.primary_cell_row = primary["row"]
                grid_entry.replica_cells = replica_cells
                grid_entry.last_seen_at = datetime.utcnow()

        except Exception as exc:
            # A grid-index failure must not discard otherwise valid search results.
            print(f"Dictionary grid indexing failed: {exc}")

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

    correction = (await db.execute(select(Correction).where(Correction.misspelled.ilike(_like_escape(norm_query), escape="\\"))
        .order_by(Correction.confidence.desc()).limit(1))).scalar_one_or_none()
    did_you_mean = None
    if correction and correction.corrected.strip().lower() != norm_query.lower():
        did_you_mean = correction.corrected.strip()

    # Typo tolerance: the elastic cloud finds near-miss words in neighbouring cells.
    suggestions: list[str] = []
    if is_single_dictionary_term and not definition and marker["face"] == "L":
        suggestions = await _cloud_suggestions(db, norm_query, lang, cloud)
        if did_you_mean is None and suggestions:
            did_you_mean = suggestions[0]

    response = {
        "query": query, "L": L, "Lsum": L, "uID": uid_chain, "S": S, "Ssum": S, "c": c,
        "primary_cell_col": primary["col"], "primary_cell_row": primary["row"],
        "cell_label": _cell_label(marker, primary["col"]), "language": lang,
        "face": marker["face"], "grid_columns": marker["columns"],
        "gsp": gsp, "elastic_cloud": cloud, "elastic_cloud_size": len(cloud),
        "definition": definition, "dictionary": dictionary, "news": news_articles,
        "wikipedia": wiki_articles, "web_results": web_results, "crawler_results": crawler_results,
        "ai_summary": ai_summary, "did_you_mean": did_you_mean, "suggestions": suggestions,
        "related_questions": [],
        "gsg_cell": gsg_data,
        "source_status": {"dictionary": bool(definition), "news": bool(news_articles),
            "wikipedia": bool(wiki_articles), "web": bool(web_results), "crawler": bool(crawler_results)},
    }
    if user:
        db.add(Search(user_id=user.id, query=query, gsp_cell=_cell_key(gsp)))
    # Cache only results that found something, and never a user's location.
    if any(response["source_status"].values()) or ai_summary:
        stored = {**response, "gsg_cell": None}
        if cached:
            cached.result = stored
            cached.cached_at = datetime.utcnow()
        else:
            db.add(SearchCache(cache_key=cache_key, result=stored, cached_at=datetime.utcnow()))
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return response
