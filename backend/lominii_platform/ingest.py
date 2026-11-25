"""Shared crawler ingestion (platform layer).

One place decides how a fetched page enters the index, whichever path
fetched it. Placement inputs are the crawler's own (L = word or text length, uID from
the 0-based letter chain), separate from user placement.

Placement happens after the external crawl and stores only start_row and c
(kept as the "c,row" cell key), by word and by full text:
  word - every token of the page -> website_tokens.gsp_cell
  text - the full page text      -> pages.gsp_cell
Letters are indexed (website_characters) but never placed. The GridCrawler
(gridcrawler.py) is search-side only: it walks the grid and never places.
"""
import re
from datetime import datetime
from hashlib import sha256

from sqlalchemy import delete

from lominii_platform.crawler import normalize_url
from lominii_platform.gsp import gsp_place, normalise
from lominii_platform.keymaps.keyboard import (
    detect_language,
    tokenize,
    word_kind,
)
from lominii_platform.models.crawler import (
    CrawlerPage,
    CrawlerWebsiteCharacter,
    CrawlerWebsiteToken,
)
from lominii_platform.placement import CrawlerPlacement

ROWS = 64
MAX_TOKENS = 50000
MAX_CHARACTERS = 250000
TOKEN_RE = re.compile(r"[^\W_]+(?:['’\-][^\W_]+)*", re.UNICODE)


def _key(face, cell):
    base = f"{cell['col']},{cell['row']}"
    return base if face == "L" else f"N:{base}"


def place_cell(text, lang, phase="word"):
    """Primary crawler cell key for text in one phase, or None if unplaceable."""
    params = CrawlerPlacement(text, lang, phase).parameters()
    face = params.get("face")
    if face not in ("L", "N"):
        return None
    cell = gsp_place(params["L"], params["S"], params["c"], K=1,
                     D=params["D"], C=params["C"], R=ROWS)["primary_cell"]
    return _key(face, cell)


def page_cell(content, lang):
    """Text phase: the page's full text."""
    return place_cell(normalise(content or "", lang), lang, "text")


def detect_lang(text, default="en"):
    try:
        return detect_language((text or "")[:2000], default=default) or default
    except Exception:
        return default


def build_index_rows(url_hash, title, content, language):
    language = (language or "en")[:16]
    tokens, chars = [], []
    word_cells = {}
    for section, text in (("title", title or ""), ("body", content or "")):
        for position, match in enumerate(TOKEN_RE.finditer(text)):
            if len(tokens) >= MAX_TOKENS and len(chars) >= MAX_CHARACTERS:
                break
            original = match.group(0)
            normalized = normalise(original, language).strip().lower()
            if not normalized or len(normalized) > 255:
                continue
            if len(tokens) < MAX_TOKENS:
                if normalized not in word_cells:
                    word_cells[normalized] = place_cell(normalized, language, "word")
                tokens.append({
                    "url_hash": url_hash,
                    "normalized_token": normalized,
                    "original_token": original,
                    "language": language,
                    "section": section,
                    "token_position": position,
                    "char_start": match.start(),
                    "kind": word_kind(normalized, language),
                    "gsp_cell": word_cells[normalized],
                })
            if len(chars) < MAX_CHARACTERS:
                for char_position, unit in enumerate(tokenize(normalized, language)):
                    chars.append({
                        "url_hash": url_hash,
                        "character": unit.value[:8],
                        "token_id": unit.index if unit.kind in ("L", "N") else None,
                        "kind": unit.kind,
                        "character_position": char_position,
                        "normalized_token": normalized,
                        "language": language,
                        "section": section,
                        "token_position": position,
                    })
    return tokens, chars[:MAX_CHARACTERS]


async def rebuild_index(db, url_hash, title, content, language):
    """Replace the word and letter rows of one page."""
    await db.execute(delete(CrawlerWebsiteToken).where(
        CrawlerWebsiteToken.url_hash == url_hash))
    await db.execute(delete(CrawlerWebsiteCharacter).where(
        CrawlerWebsiteCharacter.url_hash == url_hash))
    tokens, chars = build_index_rows(url_hash, title, content, language)
    if tokens:
        await db.execute(CrawlerWebsiteToken.__table__.insert(), tokens)
    if chars:
        await db.execute(CrawlerWebsiteCharacter.__table__.insert(), chars)


async def ingest_page(db, url, title, content, out_links=None, language=None,
                      payload=None, media_type=None):
    """Upsert one fetched page: place by full text, index words and letters."""
    url = normalize_url(url)
    if not url or not content:
        return None
    lang = language or detect_lang(content)
    url_hash = sha256(url.encode("utf-8")).hexdigest()
    page = await db.get(CrawlerPage, url_hash)
    if page is None:
        page = CrawlerPage(url_hash=url_hash, url=url, pagerank=0.0)
        db.add(page)
    page.url = url
    page.title = title
    page.content = content
    page.out_links = out_links or []
    if payload is not None:
        page.payload = payload
        page.media_type = media_type
    page.gsp_cell = page_cell(content, lang)
    page.last_crawled = datetime.utcnow()
    await db.flush()
    await rebuild_index(db, url_hash, title, content, lang)
    return page
