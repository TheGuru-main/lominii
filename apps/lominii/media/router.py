"""LOMINII ScrapingBee video discovery and online-video submissions."""

import html
import ipaddress
import json
import os
import re
import time
from datetime import datetime, timezone
from urllib.parse import quote_plus, urlparse

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from lominii_platform import ingest
from lominii_platform.database import get_db

router = APIRouter(
    prefix="/api/media/scrapingbee",
    tags=["ScrapingBee Video Discovery"],
)

SCRAPINGBEE_URL = "https://app.scrapingbee.com/api/v1/"
SCRAPINGBEE_TIMEOUT = float(
    os.getenv("SCRAPINGBEE_TIMEOUT_SECONDS", "25")
)
SCRAPINGBEE_RENDER_JS = (
    os.getenv("SCRAPINGBEE_RENDER_JS", "true").lower() == "true"
)

VIDEO_HOSTS = (
    "youtube.com",
    "youtu.be",
    "vimeo.com",
    "tiktok.com",
    "dailymotion.com",
    "twitch.tv",
)

_RATE_LIMIT = {}
RATE_WINDOW_SECONDS = 60
RATE_MAX_REQUESTS = 10


class VideoSubmission(BaseModel):
    url: str = Field(min_length=8, max_length=2048)


def check_rate_limit(request: Request):
    """Basic per-client request limit for the scraper-backed endpoints."""
    client_ip = request.client.host if request.client else "unknown"
    now = time.monotonic()

    start, count = _RATE_LIMIT.get(client_ip, (now, 0))

    if now - start >= RATE_WINDOW_SECONDS:
        start, count = now, 0

    if count >= RATE_MAX_REQUESTS:
        raise HTTPException(
            status_code=429,
            detail="Too many video requests. Please try again shortly.",
        )

    _RATE_LIMIT[client_ip] = (start, count + 1)


def validate_video_url(value: str) -> str:
    """Accept HTTPS links from supported public video platforms."""
    value = value.strip()

    try:
        parsed = urlparse(value)
        hostname = (parsed.hostname or "").lower().rstrip(".")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid video URL.")

    if (
        parsed.scheme != "https"
        or not hostname
        or parsed.username
        or parsed.password
    ):
        raise HTTPException(
            status_code=400,
            detail="Use a valid HTTPS video URL.",
        )

    try:
        ip = ipaddress.ip_address(hostname)
        if not ip.is_global:
            raise HTTPException(
                status_code=400,
                detail="Private or local addresses are not allowed.",
            )
    except ValueError:
        pass

    supported = any(
        hostname == domain or hostname.endswith("." + domain)
        for domain in VIDEO_HOSTS
    )

    if not supported:
        raise HTTPException(
            status_code=400,
            detail=(
                "This video platform is not supported yet. "
                "Try YouTube, Vimeo, TikTok, Dailymotion or Twitch."
            ),
        )

    return value


async def scrape_page(url: str) -> str:
    """Retrieve a public page through ScrapingBee."""
    api_key = os.getenv("SCRAPINGBEE_API_KEY", "").strip()

    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="Video discovery is not configured yet.",
        )

    try:
        async with httpx.AsyncClient(
            timeout=SCRAPINGBEE_TIMEOUT
        ) as client:
            response = await client.get(
                SCRAPINGBEE_URL,
                params={
                    "api_key": api_key,
                    "url": url,
                    "render_js": str(SCRAPINGBEE_RENDER_JS).lower(),
                },
            )

        if response.status_code >= 400:
            raise HTTPException(
                status_code=502,
                detail="ScrapingBee could not retrieve that page.",
            )

        return response.text[:4_000_000]

    except HTTPException:
        raise
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="Video page retrieval timed out. Please try again.",
        )
    except httpx.HTTPError:
        raise HTTPException(
            status_code=502,
            detail="Video page retrieval failed.",
        )


def decode_json_string(value: str) -> str:
    try:
        return html.unescape(json.loads('"' + value + '"')).strip()
    except (ValueError, TypeError):
        return html.unescape(value).strip()


def _field(chunk: str, key: str) -> str:
    """First text value that follows a YouTube renderer key (best effort)."""
    pos = chunk.find('"' + key + '"')
    if pos < 0:
        return ""
    found = re.search(
        r'"(?:simpleText|text)"\s*:\s*"((?:\\.|[^"\\])*)"',
        chunk[pos:pos + 600],
    )
    return decode_json_string(found.group(1)) if found else ""


def extract_suggestions(page: str, limit: int = 8) -> list:
    """Extract video results with their full payload from YouTube search HTML."""
    results = []
    seen = set()
    starts = list(re.finditer(r'"videoRenderer"\s*:\s*\{', page))
    for index, match in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else match.end() + 12000
        chunk = page[match.end():min(end, match.end() + 12000)]
        video_id = re.search(r'"videoId"\s*:\s*"([A-Za-z0-9_-]{11})"', chunk)
        title = _field(chunk, "title")
        if not video_id or not title:
            continue
        vid = video_id.group(1)
        if vid in seen:
            continue
        seen.add(vid)
        thumbnail = re.search(
            r'"thumbnails"\s*:\s*\[\s*\{\s*"url"\s*:\s*"([^"]+)"', chunk
        )
        item = {
            "title": title,
            "url": f"https://www.youtube.com/watch?v={vid}",
            "platform": "YouTube",
            "provider": "scrapingbee",
            "video_id": vid,
            "channel": _field(chunk, "ownerText"),
            "duration": _field(chunk, "lengthText"),
            "views": _field(chunk, "viewCountText"),
            "published": _field(chunk, "publishedTimeText"),
            "description": _field(chunk, "descriptionSnippet"),
        }
        if thumbnail:
            item["thumbnail"] = decode_json_string(thumbnail.group(1))
        results.append({k: v for k, v in item.items() if v})
        if len(results) >= limit:
            break
    return results


def extract_metadata(page: str, source_url: str) -> dict:
    """Extract title, description and thumbnail from page metadata."""
    meta = {}

    for tag in re.findall(r"<meta\b[^>]*>", page, re.I):
        attrs = {
            key.lower(): html.unescape(value)
            for key, quote, value in re.findall(
                r"""([\w:-]+)\s*=\s*(["'])(.*?)\2""",
                tag,
                re.I,
            )
        }

        key = (
            attrs.get("property")
            or attrs.get("name")
            or ""
        ).lower()

        if key and attrs.get("content"):
            meta[key] = attrs["content"].strip()

    title_match = re.search(
        r"<title[^>]*>(.*?)</title>",
        page,
        re.I | re.S,
    )

    title = (
        meta.get("og:title")
        or meta.get("twitter:title")
        or (
            html.unescape(re.sub(r"\s+", " ", title_match.group(1))).strip()
            if title_match else ""
        )
    )

    description = (
        meta.get("og:description")
        or meta.get("description")
        or meta.get("twitter:description")
        or ""
    )

    thumbnail = (
        meta.get("og:image")
        or meta.get("twitter:image")
        or ""
    )

    return {
        "title": title[:500],
        "description": description[:3000],
        "thumbnail": thumbnail,
        "url": source_url,
        "provider": "scrapingbee",
        "submitted_at": datetime.now(timezone.utc).isoformat(),
    }


PLATFORM_NAMES = {
    "youtube.com": "YouTube", "youtu.be": "YouTube", "vimeo.com": "Vimeo",
    "tiktok.com": "TikTok", "dailymotion.com": "Dailymotion", "twitch.tv": "Twitch",
}
VIDEO_LINK_RE = re.compile(
    r"^(?:https?://)?(?:[\w-]+\.)*(?:"
    + "|".join(re.escape(h) for h in VIDEO_HOSTS)
    + r")[/?#]\S+$",
    re.I,
)


def platform_of(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    for domain, name in PLATFORM_NAMES.items():
        if host == domain or host.endswith("." + domain):
            return name
    return "Video"


def http_match(query: str):
    """The https video URL when the query is itself a supported video link."""
    q = query.strip()
    if not VIDEO_LINK_RE.match(q):
        return None
    if not re.match(r"https?://", q, re.I):
        q = "https://" + q
    elif q[:5].lower() == "http:":
        q = "https:" + q[5:]
    try:
        return validate_video_url(q)
    except HTTPException:
        return None


async def persist_videos(db: AsyncSession, items: list) -> None:
    """Index each video in the crawler index and keep its full payload."""
    for item in items:
        try:
            body = " ".join(
                str(item[key]) for key in ("title", "description", "channel")
                if item.get(key)
            )
            await ingest.ingest_page(
                db, item["url"], item.get("title") or item["url"], body,
                payload=item, media_type="video",
            )
            await db.commit()
        except Exception as exc:
            await db.rollback()
            print(f"Video index failed: {type(exc).__name__}: {exc}")


@router.get("/suggestions")
async def video_suggestions(
    request: Request,
    q: str = Query(min_length=1, max_length=2048),
    db: AsyncSession = Depends(get_db),
):
    """Video suggestions: an http match for a video link, else a word search."""
    check_rate_limit(request)
    query = q.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Enter a search term.")

    link = http_match(query)
    if link:
        meta = extract_metadata(await scrape_page(link), link)
        suggestions = []
        if meta["title"]:
            suggestions.append({**meta, "platform": platform_of(link), "match": "http"})
    else:
        if len(query) > 120:
            raise HTTPException(status_code=400, detail="Search term too long.")
        page = await scrape_page(
            "https://www.youtube.com/results?search_query=" + quote_plus(query)
        )
        suggestions = [{**item, "match": "word"} for item in extract_suggestions(page)]

    await persist_videos(db, suggestions)
    return {
        "query": query,
        "provider": "scrapingbee",
        "match": "http" if link else "word",
        "suggestions": suggestions,
        "count": len(suggestions),
    }


@router.post("/submit")
async def submit_online_video(
    payload: VideoSubmission,
    request: Request,
):
    """Retrieve metadata for a user-submitted online video URL."""
    check_rate_limit(request)

    video_url = validate_video_url(payload.url)
    page = await scrape_page(video_url)
    metadata = extract_metadata(page, video_url)

    if not metadata["title"]:
        raise HTTPException(
            status_code=422,
            detail=(
                "No video-page title could be retrieved. "
                "The page may be private or unavailable."
            ),
        )

    return metadata
