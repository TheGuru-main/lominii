"""Admin crawler routes and bounded background worker."""

import asyncio
import re
from datetime import datetime
from html.parser import HTMLParser
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from lominii_platform.auth import get_current_user
from lominii_platform.crawler import (
    CRAWLER_ENABLED,
    CRAWLER_DEPTH,
    CRAWLER_MAX_PAGES,
    crawl_url,
    fetch_and_parse,
    is_safe_public_url,
    normalize_url,
)
from lominii_platform.database import async_session
from lominii_platform.models.crawler import CrawlerPage
from lominii_platform.pagerank import compute_pagerank

router = APIRouter(prefix="/api/admin/crawler", tags=["Admin"])

CRAWL_PAGE_HARD_CAP = 100
CRAWL_DEPTH_HARD_CAP = 3

_state = {
    "status": "idle",
    "seed": None,
    "pages_saved": 0,
    "pages_failed": 0,
    "pages_seen": 0,
    "started_at": None,
    "finished_at": None,
    "error": None,
}
_crawl_task = None


class _PageTextParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title_parts = []
        self.text_parts = []
        self.in_title = False
        self.blocked_depth = 0

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in ("script", "style", "noscript", "svg"):
            self.blocked_depth += 1
        if tag == "title":
            self.in_title = True

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in ("script", "style", "noscript", "svg"):
            self.blocked_depth = max(0, self.blocked_depth - 1)
        if tag == "title":
            self.in_title = False

    def handle_data(self, data):
        value = data.strip()
        if not value:
            return
        if self.in_title:
            self.title_parts.append(value)
        if not self.blocked_depth:
            self.text_parts.append(value)


def _extract_page(html):
    parser = _PageTextParser()
    try:
        parser.feed(html)
    except Exception:
        pass

    title = re.sub(r"\s+", " ", " ".join(parser.title_parts)).strip()
    content = re.sub(r"\s+", " ", " ".join(parser.text_parts)).strip()
    return title[:1000], content[:100000]


async def _save_page(metadata, title, content, outgoing):
    async with async_session() as session:
        page = await session.get(CrawlerPage, metadata["hash"])
        if page is None:
            page = CrawlerPage(
                url_hash=metadata["hash"],
                url=metadata["url"],
            )
            session.add(page)

        page.url = metadata["url"]
        page.gsp_cell = metadata["cell_key"][:10]
        page.title = title
        page.content = content
        page.out_links = outgoing
        page.pagerank = 0.0
        page.last_crawled = datetime.utcnow()

        await session.commit()


async def _update_pagerank(graph):
    if not graph:
        return

    scores = compute_pagerank(graph)
    if not scores:
        return

    async with async_session() as session:
        result = await session.execute(
            select(CrawlerPage).where(CrawlerPage.url.in_(list(scores)))
        )
        for page in result.scalars():
            page.pagerank = float(scores.get(page.url, 0.0))
        await session.commit()


async def _run_crawl(seed_url):
    _state.update({
        "status": "running",
        "seed": seed_url,
        "pages_saved": 0,
        "pages_failed": 0,
        "pages_seen": 0,
        "started_at": datetime.utcnow().isoformat() + "Z",
        "finished_at": None,
        "error": None,
    })

    try:
        seed_host = urlparse(seed_url).hostname.lower()
        max_pages = min(max(int(CRAWLER_MAX_PAGES), 1), CRAWL_PAGE_HARD_CAP)
        max_depth = min(max(int(CRAWLER_DEPTH), 0), CRAWL_DEPTH_HARD_CAP)

        queue = [(seed_url, 0)]
        queued = {seed_url}
        saved_pages = {}

        while queue and _state["pages_seen"] < max_pages:
            url, depth = queue.pop(0)
            _state["pages_seen"] += 1

            if not is_safe_public_url(url):
                _state["pages_failed"] += 1
                continue

            metadata = await crawl_url(url, depth=depth)
            if not metadata:
                _state["pages_failed"] += 1
                continue

            html, discovered = await fetch_and_parse(url)
            if html is None:
                _state["pages_failed"] += 1
                continue

            title, content = _extract_page(html)

            same_site_links = []
            for link in discovered:
                parsed = urlparse(link)
                if (
                    parsed.hostname
                    and parsed.hostname.lower() == seed_host
                    and link not in same_site_links
                ):
                    same_site_links.append(link)

            try:
                await _save_page(
                    metadata, title, content, same_site_links
                )
            except Exception:
                _state["pages_failed"] += 1
                continue

            _state["pages_saved"] += 1
            saved_pages[url] = {
                "url": url,
                "outgoing_links": same_site_links,
            }

            if depth < max_depth:
                for link in same_site_links:
                    if link not in queued and len(queued) < max_pages * 5:
                        queued.add(link)
                        queue.append((link, depth + 1))

        crawled_urls = set(saved_pages)
        graph = {
            url: [
                link for link in page["outgoing_links"]
                if link in crawled_urls
            ]
            for url, page in saved_pages.items()
        }
        await _update_pagerank(graph)

        _state["status"] = "completed"

    except Exception as exc:
        _state["status"] = "failed"
        _state["error"] = str(exc)[:300]

    finally:
        _state["finished_at"] = datetime.utcnow().isoformat() + "Z"


@router.post("/start")
async def start_crawler(
    seed_url: str,
    email: str = Depends(get_current_user),
):
    global _crawl_task

    if not CRAWLER_ENABLED:
        raise HTTPException(status_code=400, detail="Crawler is disabled")

    seed_url = normalize_url(seed_url)
    if not seed_url or not is_safe_public_url(seed_url):
        raise HTTPException(
            status_code=400,
            detail="Seed must be a valid public HTTP/HTTPS URL.",
        )

    if _crawl_task is not None and not _crawl_task.done():
        raise HTTPException(
            status_code=409,
            detail="A crawl is already running.",
        )

    _crawl_task = asyncio.create_task(_run_crawl(seed_url))
    return {
        "message": "Crawler job accepted",
        "seed": seed_url,
        "status": "running",
        "limits": {
            "max_pages": min(
                max(int(CRAWLER_MAX_PAGES), 1), CRAWL_PAGE_HARD_CAP
            ),
            "max_depth": min(
                max(int(CRAWLER_DEPTH), 0), CRAWL_DEPTH_HARD_CAP
            ),
        },
    }


@router.get("/status")
async def crawler_status(
    email: str = Depends(get_current_user),
):
    return {
        "enabled": CRAWLER_ENABLED,
        **_state,
    }
