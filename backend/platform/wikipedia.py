"""Wikipedia API Service (Platform Layer)"""
import httpx

WIKI_SEARCH_URL = "https://en.wikipedia.org/w/api.php"
WIKI_SUMMARY_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/"

async def search_wikipedia(query: str, lang: str = "en", limit: int = 3) -> list[dict]:
    """
    Search Wikipedia for the given query and return a list of article summaries.
    Each dict contains: title, extract, url.
    """
    # Step 1 – search for article titles
    params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "format": "json",
        "srlimit": limit,
        "srprop": "",
    }
    async with httpx.AsyncClient(timeout=15) as client:
        # Search
        resp = await client.get(WIKI_SEARCH_URL, params=params)
        if resp.status_code != 200:
            return []
        data = resp.json()
        titles = [r["title"] for r in data.get("query", {}).get("search", [])]

        # Step 2 – get summaries for each title
        results = []
        for title in titles:
            try:
                sum_resp = await client.get(f"{WIKI_SUMMARY_URL}{title}")
                if sum_resp.status_code == 200:
                    sdata = sum_resp.json()
                    results.append({
                        "title": title,
                        "extract": sdata.get("extract", "")[:500],  # limit length
                        "url": sdata.get("content_urls", {}).get("desktop", {}).get("page", "")
                    })
            except Exception:
                continue
        return results