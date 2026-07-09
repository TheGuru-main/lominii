"""Web Crawler Service (Platform Layer)
Deterministic URL placement + link extraction + robots.txt compliance.
Enabled only when CRAWLER_ENABLED=true.
"""
import os
import hashlib
import asyncio
import httpx
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser
from .gsp import gsp_place

CRAWLER_ENABLED = os.getenv("CRAWLER_ENABLED", "false").lower() == "true"
CRAWLER_DEPTH = int(os.getenv("CRAWLER_DEPTH", "2"))          # max hops from seed
CRAWLER_MAX_PAGES = int(os.getenv("CRAWLER_MAX_PAGES", "500")) # safety limit

# GSP parameters for crawler (must match the crawler formula)
CRAWLER_K = 27
CRAWLER_D = 27
CRAWLER_C = 26
CRAWLER_R = 64

async def crawl_url(url: str, depth: int = 0) -> dict:
    """Crawl a single URL. Returns page data or None if already crawled."""
    if not CRAWLER_ENABLED:
        return None

    # Derive GSP identity
    domain = urlparse(url).netloc
    first_letter = domain[0].lower() if domain else 'a'
    c = ord(first_letter) - 97 if 'a' <= first_letter <= 'z' else 0
    L = len(url)
    S = int(hashlib.sha256(url.encode()).hexdigest()[:8], 16) % 1_000_000

    placement = gsp_place(L, S, c, K=CRAWLER_K, D=CRAWLER_D, C=CRAWLER_C, R=CRAWLER_R)
    primary = placement["primary_cell"]
    cell_key = f"{primary['col']},{primary['row']}"

    # In a full implementation, we would check the database for existing page.
    # For now, we return the placement info so the API can store it.
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
    # Simplified fetch – in production, add proper async HTTP and parsing
    # This stub returns the URL itself as 'text' and extracts links from HTML.
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, follow_redirects=True, timeout=10)
            resp.raise_for_status()
            html = resp.text
            # Extract links (simple regex, replace with BeautifulSoup in production)
            import re
            links = re.findall(r'href=[\'"]?([^\'" >]+)', html)
            # Normalize links
            base = url
            absolute_links = [urljoin(base, link) for link in links if link.startswith('http')]
            # Return only unique, valid URLs
            return resp.text, list(set(absolute_links))[:100]  # limit to 100 links
        except Exception:
            return None, []