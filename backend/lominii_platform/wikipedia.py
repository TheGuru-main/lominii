"""Language-aware Wikipedia search and bounded article summaries."""
import asyncio
from urllib.parse import quote
import httpx

SUPPORTED_WIKI_LANGUAGES = {"en", "fr", "de"}

async def search_wikipedia(query: str, lang: str = "en", limit: int = 3) -> list[dict]:
    """Search the selected language's Wikipedia; source failure returns an empty list."""
    query = (query or "").strip()
    if not query:
        return []
    language = (lang or "en").lower().split("-", 1)[0]
    if language not in SUPPORTED_WIKI_LANGUAGES:
        language = "en"
    limit = max(1, min(int(limit), 5))
    base = f"https://{language}.wikipedia.org"
    params = {"action": "query", "list": "search", "srsearch": query,
              "format": "json", "srlimit": limit, "srprop": ""}
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(8.0, connect=3.0)) as client:
            response = await client.get(f"{base}/w/api.php", params=params)
            if response.status_code != 200:
                return []
            payload = response.json()
            titles = [item.get("title") for item in payload.get("query", {}).get("search", [])
                      if isinstance(item, dict) and item.get("title")]
            if not titles:
                return []
            async def fetch_summary(title: str):
                try:
                    summary_response = await client.get(
                        f"{base}/api/rest_v1/page/summary/{quote(title, safe='')}"
                    )
                    if summary_response.status_code != 200:
                        return None
                    summary = summary_response.json()
                    urls = summary.get("content_urls", {}).get("desktop", {})
                    return {"title": summary.get("title") or title,
                            "extract": (summary.get("extract") or "")[:500],
                            "url": urls.get("page") or "", "source": "Wikipedia"}
                except Exception:
                    return None
            summaries = await asyncio.gather(*(fetch_summary(title) for title in titles),
                                              return_exceptions=True)
            return [item for item in summaries if isinstance(item, dict)
                    and item.get("title") and item.get("url")]
    except Exception:
        return []
