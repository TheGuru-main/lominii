"""Web Crawler Service (Platform Layer)
Deterministic URL placement + link extraction.
Enabled only when CRAWLER_ENABLED=true.
"""
import os
import hashlib
import asyncio
import httpx
import re
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser
from .gsp import gsp_place

CRAWLER_ENABLED = os.getenv("CRAWLER_ENABLED", "false").lower() == "true"
CRAWLER_DEPTH = int(os.getenv("CRAWLER_DEPTH", "2"))
CRAWLER_MAX_PAGES = int(os.getenv("CRAWLER_MAX_PAGES", "500"))

CRAWLER_K = 27
CRAWLER_D = 27
CRAWLER_C = 26
CRAWLER_R = 64

async def crawl_url(url: str, depth: int = 0) -> dict:
    """Crawl a single URL. Returns page data or None if already crawled."""
    if not CRAWLER_ENABLED:
        return None

    domain = urlparse(url).netloc
    first_letter = domain[0].lower() if domain else 'a'
    c = ord(first_letter) - 97 if 'a' <= first_letter <= 'z' else 0
    L = len(url)
    S = int(hashlib.sha256(url.encode()).hexdigest()[:8], 16) % 1_000_000

    placement = gsp_place(L, S, c, K=CRAWLER_K, D=CRAWLER_D, C=CRAWLER_C, R=CRAWLER_R)
    primary = placement["primary_cell"]
    cell_key = f"{primary['col']},{primary['row']}"

    return {
        "url": url,
        "cell": primary,
        "cell_key": cell_key,
        "L": L,
        "S": S,
        "c": c
    }

async def fetch_and_parse(url: str) -> tuple:
    """Fetch a page and return (text, links). Respects robots.txt."""
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, follow_redirects=True, timeout=10)
            resp.raise_for_status()
            html = resp.text
            links = re.findall(r'href=[\'"]?([^\'" >]+)', html)
            base = url
            absolute_links = [urljoin(base, link) for link in links if link.startswith('http')]
            return resp.text, list(set(absolute_links))[:100]
        except Exception:
            return None, []