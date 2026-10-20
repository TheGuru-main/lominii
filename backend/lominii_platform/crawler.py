"""
Web Crawler Service (Platform Layer)

Deterministic URL placement + graph construction.
Enabled only when CRAWLER_ENABLED=true.
"""

import os
import hashlib
import ipaddress
import socket
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

HTTP_FETCH_TIMEOUT_SECONDS = float(os.getenv("HTTP_FETCH_TIMEOUT_SECONDS", "10"))
HTTP_FETCH_MAX_REDIRECTS = int(os.getenv("HTTP_FETCH_MAX_REDIRECTS", "5"))
HTTP_FETCH_MAX_BYTES = int(os.getenv("HTTP_FETCH_MAX_BYTES", "2000000"))
HTTP_FETCH_MAX_LINKS = int(os.getenv("HTTP_FETCH_MAX_LINKS", "100"))
HTTP_FETCH_USER_AGENT = os.getenv("HTTP_FETCH_USER_AGENT", "LOMINII-Crawler/1.0")

CRAWLER_K = 27
CRAWLER_D = 27
CRAWLER_C = 56
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


def is_safe_public_url(url: str) -> bool:
    """Reject unsupported URLs and hosts resolving to non-public IPs."""
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        if not parsed.hostname or parsed.username or parsed.password:
            return False
        if parsed.port is not None:
            expected_port = 443 if parsed.scheme == "https" else 80
            if parsed.port != expected_port:
                return False

        host = parsed.hostname.rstrip(".").lower()
        if host == "localhost" or host.endswith(".localhost"):
            return False
        if host.endswith(".local"):
            return False

        try:
            addresses = [ipaddress.ip_address(host)]
        except ValueError:
            addresses = [
                ipaddress.ip_address(item[4][0])
                for item in socket.getaddrinfo(
                    host, parsed.port or (443 if parsed.scheme == "https" else 80),
                    type=socket.SOCK_STREAM,
                )
            ]

        return bool(addresses) and all(ip.is_global for ip in addresses)
    except (ValueError, OSError, socket.gaierror):
        return False


async def fetch_and_parse(url: str):
    """Fetch bounded HTML, checking each redirect before following it."""
    url = normalize_url(url)
    if not url or not is_safe_public_url(url):
        return None, []

    original_host = urlparse(url).hostname.lower()
    current = url

    try:
        async with httpx.AsyncClient(
            follow_redirects=False,
            timeout=HTTP_FETCH_TIMEOUT_SECONDS,
            headers={"User-Agent": HTTP_FETCH_USER_AGENT},
        ) as client:
            for _ in range(max(0, HTTP_FETCH_MAX_REDIRECTS) + 1):
                if not is_safe_public_url(current):
                    return None, []

                parsed_current = urlparse(current)
                if parsed_current.hostname.lower() != original_host:
                    return None, []

                async with client.stream("GET", current) as response:
                    if response.status_code in (301, 302, 303, 307, 308):
                        location = response.headers.get("location")
                        if not location:
                            return None, []
                        target = normalize_url(urljoin(current, location))
                        if not target:
                            return None, []
                        if urlparse(target).hostname.lower() != original_host:
                            return None, []
                        if not is_safe_public_url(target):
                            return None, []
                        current = target
                        continue

                    response.raise_for_status()

                    content_type = response.headers.get(
                        "content-type", ""
                    ).lower()
                    if content_type and not (
                        "text/html" in content_type
                        or "application/xhtml+xml" in content_type
                    ):
                        return None, []

                    length = response.headers.get("content-length")
                    if length:
                        try:
                            if int(length) > HTTP_FETCH_MAX_BYTES:
                                return None, []
                        except ValueError:
                            pass

                    chunks = []
                    total = 0
                    async for chunk in response.aiter_bytes():
                        total += len(chunk)
                        if total > HTTP_FETCH_MAX_BYTES:
                            return None, []
                        chunks.append(chunk)

                    encoding = response.encoding or "utf-8"
                    html = b"".join(chunks).decode(
                        encoding, errors="replace"
                    )
                    break
            else:
                return None, []

        hrefs = re.findall(
            r"""href\s*=\s*["']?([^"' >]+)""",
            html,
            flags=re.IGNORECASE,
        )

        links = []
        for href in hrefs:
            if href.lower().startswith(
                ("mailto:", "javascript:", "tel:", "data:")
            ):
                continue
            absolute = normalize_url(urljoin(current, href))
            if absolute:
                links.append(absolute)

        links = list(dict.fromkeys(links))
        return html, links[:max(0, HTTP_FETCH_MAX_LINKS)]

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