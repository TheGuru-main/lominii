"""
Web Crawler Service (Platform Layer)

Deterministic URL placement + graph construction.
Enabled only when CRAWLER_ENABLED=true.
"""

import os
import hashlib
import re

import httpx

from urllib.parse import (
    urljoin,
    urlparse,
    urldefrag,
)

from .gsp import gsp_place


CRAWLER_ENABLED = (
    os.getenv("CRAWLER_ENABLED", "false").lower() == "true"
)

CRAWLER_DEPTH = int(os.getenv("CRAWLER_DEPTH", "2"))
CRAWLER_MAX_PAGES = int(os.getenv("CRAWLER_MAX_PAGES", "500"))

CRAWLER_K = 27
CRAWLER_D = 27
CRAWLER_C = 26
CRAWLER_R = 64


# ==========================================================
# URL NORMALIZATION
# ==========================================================

def normalize_url(url: str) -> str:
    """
    Normalize a URL before storing.
    """

    url, _ = urldefrag(url)

    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https"):
        return ""

    normalized = parsed._replace(fragment="").geturl()

    return normalized.rstrip("/")


# ==========================================================
# PAGE PLACEMENT
# ==========================================================

async def crawl_url(url: str, depth: int = 0) -> dict:
    """
    Build crawler metadata for a page.
    """

    if not CRAWLER_ENABLED:
        return None

    url = normalize_url(url)

    if not url:
        return None

    domain = urlparse(url).netloc

    first_letter = domain[0].lower() if domain else "a"

    c = (
        ord(first_letter) - 97
        if "a" <= first_letter <= "z"
        else 0
    )

    L = len(url)

    S = (
        int(
            hashlib.sha256(url.encode()).hexdigest()[:8],
            16,
        )
        % 1_000_000
    )

    placement = gsp_place(
        L,
        S,
        c,
        K=CRAWLER_K,
        D=CRAWLER_D,
        C=CRAWLER_C,
        R=CRAWLER_R,
    )

    primary = placement["primary_cell"]

    return {
        "url": url,
        "domain": domain,
        "cell": primary,
        "cell_key": f"{primary['col']},{primary['row']}",
        "L": L,
        "S": S,
        "c": c,

        # Graph metadata
        "hash": hashlib.sha256(url.encode()).hexdigest(),
        "pagerank": 0.0,
        "outgoing_links": [],
        "incoming_links": [],
        "crawl_depth": depth,
    }


# ==========================================================
# FETCH + LINK EXTRACTION
# ==========================================================

async def fetch_and_parse(url: str):
    """
    Fetch a page and return:

    (
        page_html,
        outgoing_links
    )
    """

    async with httpx.AsyncClient() as client:

        try:

            response = await client.get(
                url,
                follow_redirects=True,
                timeout=10,
            )

            response.raise_for_status()

            html = response.text

            hrefs = re.findall(
                r'href=[\'"]?([^\'" >]+)',
                html,
            )

            links = []

            for href in hrefs:

                if href.startswith(("mailto:", "javascript:", "tel:")):
                    continue

                absolute = urljoin(url, href)

                absolute = normalize_url(absolute)

                if not absolute:
                    continue

                links.append(absolute)

            links = list(dict.fromkeys(links))

            return html, links[:100]

        except Exception:

            return None, []


# ==========================================================
# GRAPH BUILDER
# ==========================================================

def build_graph(crawled_pages: list[dict]) -> dict:
    """
    Build PageRank graph.

    Returns:

    {
        page_url: [linked_page1, linked_page2]
    }
    """

    graph = {}

    for page in crawled_pages:

        graph[page["url"]] = page.get(
            "outgoing_links",
            [],
        )

    return graph