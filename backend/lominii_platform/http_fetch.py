"""Safe compatibility wrapper for search page fetching."""

from html.parser import HTMLParser
from lominii_platform.crawler import fetch_and_parse


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title_parts = []
        self.text_parts = []
        self.in_title = False
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag == "title":
            self.in_title = True
        if tag in {"script", "style", "noscript", "svg", "iframe"}:
            self.skip_depth += 1

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag == "title":
            self.in_title = False
        if tag in {"script", "style", "noscript", "svg", "iframe"}:
            self.skip_depth = max(0, self.skip_depth - 1)

    def handle_data(self, data):
        text = " ".join((data or "").split())
        if not text:
            return
        if self.in_title:
            self.title_parts.append(text)
        if not self.skip_depth:
            self.text_parts.append(text)


async def fetch_public_page(url: str) -> dict | None:
    html, _ = await fetch_and_parse(url)

    if not html:
        return None

    parser = TextExtractor()
    try:
        parser.feed(html)
    except Exception:
        return None

    content = " ".join(parser.text_parts)
    if not content:
        return None

    return {
        "url": url,
        "title": " ".join(parser.title_parts).strip()[:300] or url,
        "content": content[:500_000],
    }
