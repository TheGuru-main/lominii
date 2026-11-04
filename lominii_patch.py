from pathlib import Path
import shutil
from datetime import datetime

ROOT = Path.cwd()
BACKUP = ROOT / "BK" / (
    "backend_patch_" + datetime.now().strftime("%Y%m%d_%H%M%S")
)
BACKUP.mkdir(parents=True, exist_ok=True)


def patch_file(relative_path, transform):
    path = ROOT / relative_path
    if not path.is_file():
        raise FileNotFoundError(relative_path)

    original = path.read_text(encoding="utf-8")
    updated = transform(original)

    if updated == original:
        print("UNCHANGED:", relative_path)
        return

    backup = BACKUP / relative_path
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, backup)
    path.write_text(updated, encoding="utf-8")
    print("PATCHED:", relative_path)


def fix_ai_import(source):
    if "    Boolean," in source:
        return source

    anchor = "    Column,\n    String,"
    if anchor not in source:
        raise RuntimeError("AI model import section not found")

    return source.replace(
        anchor, "    Column,\n    Boolean,\n    String,", 1
    )


def fix_crawler(source):
    source = source.replace(
        'CRAWLER_MAX_PAGES = int(os.getenv("CRAWLER_MAX_PAGES", "500"))\n\n'
        "CRAWLER_K = 27\n"
        "CRAWLER_D = 27\n"
        "CRAWLER_C = 26\n"
        "CRAWLER_R = 64",
        'CRAWLER_MAX_PAGES = int(os.getenv("CRAWLER_MAX_PAGES", "500"))\n\n'
        'HTTP_FETCH_TIMEOUT_SECONDS = float(os.getenv("HTTP_FETCH_TIMEOUT_SECONDS", "10"))\n'
        'HTTP_FETCH_MAX_REDIRECTS = int(os.getenv("HTTP_FETCH_MAX_REDIRECTS", "5"))\n'
        'HTTP_FETCH_MAX_BYTES = int(os.getenv("HTTP_FETCH_MAX_BYTES", "2000000"))\n'
        'HTTP_FETCH_MAX_LINKS = int(os.getenv("HTTP_FETCH_MAX_LINKS", "100"))\n'
        'HTTP_FETCH_USER_AGENT = os.getenv("HTTP_FETCH_USER_AGENT", "LOMINII-Crawler/1.0")\n\n'
        "CRAWLER_K = 27\n"
        "CRAWLER_D = 27\n"
        "CRAWLER_C = 56\n"
        "CRAWLER_R = 64",
        1,
    )

    start = source.find("async def fetch_and_parse(url: str):")
    marker = "\n\n# ==========================================================\n# GRAPH BUILDER"
    end = source.find(marker, start)

    if start < 0 or end < 0:
        raise RuntimeError("Crawler fetch function boundaries not found")

    replacement = '''async def fetch_and_parse(url: str):
    """Fetch HTML using configured HTTP limits and extract links."""
    url = normalize_url(url)
    if not url:
        return None, []

    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            max_redirects=HTTP_FETCH_MAX_REDIRECTS,
            timeout=HTTP_FETCH_TIMEOUT_SECONDS,
            headers={"User-Agent": HTTP_FETCH_USER_AGENT},
        ) as client:
            async with client.stream("GET", url) as response:
                response.raise_for_status()

                content_type = response.headers.get("content-type", "").lower()
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

                html = b"".join(chunks).decode(
                    response.encoding or "utf-8",
                    errors="replace",
                )

        hrefs = re.findall(
            r"""href\\s*=\\s*["']?([^"' >]+)""",
            html,
            flags=re.IGNORECASE,
        )
        links = []
        for href in hrefs:
            if href.lower().startswith(
                ("mailto:", "javascript:", "tel:", "data:")
            ):
                continue
            absolute = normalize_url(urljoin(url, href))
            if absolute:
                links.append(absolute)

        links = list(dict.fromkeys(links))
        return html, links[:max(0, HTTP_FETCH_MAX_LINKS)]

    except Exception:
        return None, []
'''

    return source[:start] + replacement + source[end:]


patch_file("backend/lominii_platform/models/ai.py", fix_ai_import)
patch_file("backend/lominii_platform/crawler.py", fix_crawler)

print("Backup directory:", BACKUP)
print("Patch stage complete.")
