"""GridCrawler: search-side walker over the GSP grid. It never places or stores.

From the cell where a query lands it walks K=250 steps of row step D=8 and
returns the cells it passes through (about 104 distinct on a 26-column grid).
Search then looks up stored entries, which were placed only by start_row and c,
in those cells. Entry points:
  word   - walk from the word's cell
  text   - walk from the full text's cell
  letter - no GSP calculation: a letter is only its 0-based index marker
"""
from lominii_platform.keymaps.keyboard import tokenize
from lominii_platform.placement import CRAWLER_D, CRAWLER_K, CrawlerPlacement

GRID_K = CRAWLER_K
GRID_D = CRAWLER_D


def cell_key(face, cell):
    base = f"{cell['col']},{cell['row']}"
    return base if face == "L" else f"N:{base}"


def walk(text, lang="en", entry="word"):
    """Distinct cell keys visited from the entry cell, in walk order."""
    placement = CrawlerPlacement(text, lang, entry)
    face = placement.parameters().get("face")
    if face not in ("L", "N"):
        return []
    keys = []
    for cell in placement.compute()["cells"]:
        key = cell_key(face, cell)
        if key not in keys:
            keys.append(key)
    return keys


def letter_entry(letter, lang="en"):
    """Letter entry point: its kind and 0-based index marker (the token id)."""
    for unit in tokenize(letter, lang):
        if unit.kind in ("L", "N"):
            return {"kind": unit.kind, "token_id": unit.index}
    return None
