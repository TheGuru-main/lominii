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
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

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


def extract_suggestions(page: str, limit: int = 8) -> list:
    """Extract accessible video titles and links from YouTube search HTML."""
    results = []
    seen = set()

    starts = list(
        re.finditer(r'"videoRenderer"\s*:\s*\{', page)
    )

    for index, match in enumerate(starts):
        end = (
            starts[index + 1].start()
            if index + 1 < len(starts)
            else match.end() + 12000
        )
        chunk = page[match.end():min(end, match.end() + 12000)]

        video_id = re.search(
            r'"videoId"\s*:\s*"([A-Za-z0-9_-]{11})"',
            chunk,
        )
        title_match = re.search(
            r'"title"\s*:\s*\{\s*"runs"\s*:\s*'
            r'\[\s*\{\s*"text"\s*:\s*"((?:\\.|[^"\\])*)"',
            chunk,
        )

        if not video_id or not title_match:
            continue

        vid = video_id.group(1)
        title = decode_json_string(title_match.group(1))

        if not title or vid in seen:
            continue

        seen.add(vid)

        thumbnail = re.search(
            r'"thumbnails"\s*:\s*\[\s*\{\s*"url"\s*:\s*"([^"]+)"',
            chunk,
        )

        item = {
            "title": title,
            "url": f"https://www.youtube.com/watch?v={vid}",
            "platform": "YouTube",
            "provider": "scrapingbee",
        }

        if thumbnail:
            item["thumbnail"] = decode_json_string(
                thumbnail.group(1)
            )

        results.append(item)

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


@router.get("/suggestions")
async def video_suggestions(
    request: Request,
    q: str = Query(min_length=1, max_length=120),
):
    """Discover public YouTube results through ScrapingBee."""
    check_rate_limit(request)

    query = q.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Enter a search term.")

    search_url = (
        "https://www.youtube.com/results?search_query="
        + quote_plus(query)
    )

    page = await scrape_page(search_url)
    suggestions = extract_suggestions(page)

    return {
        "query": query,
        "provider": "scrapingbee",
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
