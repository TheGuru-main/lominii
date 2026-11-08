"""Boot-time dictionary seeding for the GSP grid.

At start-up (and again whenever new vocabulary appears) this crawls dictionary
details from the external dictionary API and persists each headword on the grid:
GSP placement, lexical tokens and letter index, plus grid snapshots. Search then
finds entries by GSP placement and by lexical tokens instead of waiting for
someone to search each word first.

Where the words come from, in this order:
  1. what people searched and the corrections the app has learned
  2. a built-in starter list, an optional file, and an optional remote list
  3. words the crawler found on pages and in news titles
  4. words used inside definitions already indexed (the lexicon grows itself)

The crawl is polite (a fixed rate), resumable (words already indexed or recently
missing are skipped), and runs in one instance only (a database advisory lock).
Everything it does is logged and shown at /api/search/status.
"""
import asyncio
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote

import httpx
from sqlalchemy import func, select, text

from lominii_platform.database import async_session, engine
from lominii_platform.gsp import normalise
from lominii_platform.keymaps.keyboard import tokenize
from lominii_platform.models.crawler import CrawlerWebsiteToken
from lominii_platform.models.search import (
    Correction, DictionaryCache, DictionaryGridEntry, DictionaryLexicalToken,
    NewsArticle, Search,
)
from apps.lominii.search import router as search_router

API_LANGUAGES = {"en", "fr", "de"}  # languages the external dictionary API serves
MISS_DAYS = 7                       # how long a "no entry" answer is trusted
LOCK_KEY = 7740011223
STATE = search_router.SEEDER_STATE

STARTER_WORDS = {
    "en": """time person year way day thing man world life hand part child eye woman place work
        week case point government company number group problem fact water money story book word
        business night house family city school friend music light door road river food market
        garden window mother father sister brother teacher doctor farmer village country language
        dream season winter summer morning evening health power moment idea reason answer question
        change energy memory nature animal bird tree flower mountain ocean island bridge machine
        engine paper letter picture voice silence courage wisdom freedom justice peace honest
        simple gentle ancient modern quiet bright strong""".split(),
    "fr": """maison famille ami enfant homme femme jour nuit temps monde ville pays eau pain livre
        école travail amour vie main tête cœur porte route rivière jardin fenêtre mère père soeur
        frère médecin village langue rêve saison hiver été matin soir santé idée raison réponse
        question changement nature animal oiseau arbre fleur montagne océan île pont machine
        papier lettre image voix silence courage sagesse liberté justice paix""".split(),
    "de": """haus familie freund kind mann frau tag nacht zeit welt stadt land wasser brot buch
        schule arbeit liebe leben hand kopf herz auge tür straße fluss garten fenster mutter
        vater schwester bruder lehrer arzt dorf sprache traum jahreszeit winter sommer morgen
        abend gesundheit idee grund antwort frage veränderung natur tier vogel baum blume berg
        meer insel brücke maschine papier brief bild stimme stille mut weisheit freiheit
        gerechtigkeit frieden""".split(),
}

_remote_cache: dict[str, list[str]] = {}


def _int_env(name: str, default: int, low: int, high: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        value = default
    return max(low, min(value, high))


def enabled() -> bool:
    return os.getenv("DICTIONARY_SEED_ENABLED", "1").strip().lower() not in {"0", "false", "no", "off"}


def seed_languages() -> list[str]:
    wanted = [item.strip().lower() for item in os.getenv("DICTIONARY_SEED_LANGS", "en,fr,de").split(",")]
    return [item for item in dict.fromkeys(wanted) if item in API_LANGUAGES]


def per_minute() -> int:
    return _int_env("DICTIONARY_SEED_PER_MINUTE", 30, 1, 60)


def batch_size() -> int:
    return _int_env("DICTIONARY_SEED_BATCH", 20, 1, 100)


def idle_seconds() -> int:
    return _int_env("DICTIONARY_SEED_IDLE_SECONDS", 3600, 60, 86400)


def clean_word(raw, lang: str):
    """A single lower-case word made only of the language's own letters, or None."""
    word = normalise(str(raw or ""), lang).strip()
    if not (2 <= len(word) <= 40) or not word.isalpha():
        return None
    tokens = tokenize(word, lang)
    if len(tokens) < 2 or any(token.kind != "L" for token in tokens):
        return None
    return word


def _file_words(lang: str) -> list[str]:
    path = Path(os.getenv("DICTIONARY_SEED_DIR", "seed_words")) / f"{lang}.txt"
    try:
        return path.read_text(encoding="utf-8").splitlines()[:50000]
    except OSError:
        return []


async def _remote_words(client, lang: str) -> list[str]:
    url = os.getenv(f"DICTIONARY_SEED_URL_{lang.upper()}", "").strip()
    if not url.lower().startswith("https://"):
        return []
    if lang in _remote_cache:
        return _remote_cache[lang]
    words: list[str] = []
    try:
        response = await client.get(url)
        if response.status_code == 200 and len(response.content) <= 2_000_000:
            words = [line.strip() for line in response.text.splitlines()[:50000]]
        else:
            print(f"Dictionary seeder: word list for {lang} returned HTTP {response.status_code}")
    except Exception as exc:
        print(f"Dictionary seeder: word list for {lang} unavailable: {type(exc).__name__}")
    _remote_cache[lang] = words
    return words


async def _rows(db, statement):
    """Run one signal query; a missing table or column skips that signal only."""
    try:
        return (await db.execute(statement)).all()
    except Exception as exc:
        await db.rollback()
        print(f"Dictionary seeder: signal query skipped ({type(exc).__name__})")
        return []


async def gather_candidates(db, lang: str, want: int, extra_words=()) -> list[str]:
    """Next words worth crawling: not indexed yet and not recently found missing."""
    ordered: list[str] = []
    seen: set[str] = set()

    def take(words):
        for raw in words:
            word = clean_word(raw, lang)
            if word and word not in seen:
                seen.add(word)
                ordered.append(word)

    rows = await _rows(db, select(Search.query).order_by(Search.id.desc()).limit(3000))
    take(row[0] for row in rows if row[0] and len(str(row[0]).split()) == 1)

    rows = await _rows(db, select(Correction.corrected).limit(2000))
    take(row[0] for row in rows)

    take(STARTER_WORDS.get(lang, []))
    take(_file_words(lang))
    take(extra_words)

    rows = await _rows(db, (
        select(CrawlerWebsiteToken.normalized_token, func.count().label("n"))
        .where(CrawlerWebsiteToken.language == lang, CrawlerWebsiteToken.kind == "L")
        .group_by(CrawlerWebsiteToken.normalized_token)
        .order_by(func.count().desc()).limit(3000)
    ))
    take(row[0] for row in rows)

    rows = await _rows(db, select(NewsArticle.title).order_by(NewsArticle.id.desc()).limit(300))
    for row in rows:
        take(re.findall(r"[^\W\d_]+", str(row[0] or "").lower(), flags=re.UNICODE))

    rows = await _rows(db, (
        select(DictionaryLexicalToken.normalized_token, func.count().label("n"))
        .where(DictionaryLexicalToken.language == lang, DictionaryLexicalToken.token_type == "meaning")
        .group_by(DictionaryLexicalToken.normalized_token)
        .order_by(func.count().desc()).limit(3000)
    ))
    take(row[0] for row in rows)

    fresh: list[str] = []
    cutoff = datetime.utcnow() - timedelta(days=MISS_DAYS)
    for start in range(0, len(ordered), 400):
        chunk = ordered[start:start + 400]
        known = {row[0] for row in await _rows(db, select(DictionaryGridEntry.normalized_word).where(
            DictionaryGridEntry.language == lang,
            DictionaryGridEntry.normalized_word.in_(chunk)))}
        missed = {
            str(row[0]).split(":", 1)[-1]
            for row in await _rows(db, select(DictionaryCache.word, DictionaryCache.cached_at).where(
                DictionaryCache.word.in_([f"{lang}:{word}" for word in chunk]),
                func.coalesce(DictionaryCache.definition, "") == ""))
            if row[1] and row[1] > cutoff
        }
        fresh += [word for word in chunk if word not in known and word not in missed]
        if len(fresh) >= want:
            break
    return fresh[:want]


async def fetch_entry(client, lang: str, word: str):
    """("ok", entry) | ("miss", None) | ("rate", None) | ("error", None)."""
    url = f"https://api.dictionaryapi.dev/api/v2/entries/{lang}/{quote(word, safe='')}"
    try:
        response = await client.get(url)
    except Exception:
        return "error", None
    if response.status_code == 429:
        return "rate", None
    if response.status_code == 404:
        return "miss", None
    if response.status_code != 200:
        return "error", None
    try:
        payload = response.json()
    except ValueError:
        return "error", None
    definition, details = search_router._dictionary_payload(payload)
    if not definition or not details:
        return "miss", None
    source_url = None
    first = payload[0] if isinstance(payload, list) and payload and isinstance(payload[0], dict) else {}
    urls = first.get("sourceUrls")
    if isinstance(urls, list) and urls and isinstance(urls[0], str):
        source_url = urls[0]
    return "ok", {
        "word": word,
        "definition": definition,
        "phonetic": details.get("phonetic") or "",
        "part_of_speech": details.get("part_of_speech") or "",
        "source": "dictionaryapi.dev",
        "source_url": source_url,
    }


async def persist_batch(lang: str, found: list, missed: list) -> int:
    """Write found entries (grid, lexical tokens, letters, snapshots) and remember misses."""
    async with async_session() as db:
        try:
            saved = 0
            for item in found:
                outcome, entry = await search_router._upsert_dictionary_entry(db, lang, item)
                if entry is None:
                    continue
                await search_router._rebuild_dictionary_lexical_indexes(db, entry)
                saved += 1
            now = datetime.utcnow()
            for word in missed:
                key = f"{lang}:{word}"[:255]
                row = (await db.execute(
                    select(DictionaryCache).where(DictionaryCache.word == key)
                )).scalar_one_or_none()
                if row is None:
                    db.add(DictionaryCache(word=key, definition="", language=lang, cached_at=now))
                elif not (row.definition or ""):
                    row.cached_at = now
            await db.flush()
            await search_router._create_dictionary_grid_snapshots(db, checkpoint_size=2000)
            await db.commit()
            return saved
        except Exception as exc:
            await db.rollback()
            STATE["last_error"] = f"{type(exc).__name__}: {str(exc)[:200]}"
            print(f"Dictionary seeder: saving a batch failed: {STATE['last_error']}")
            return 0


async def seed_language(client, lang: str) -> int:
    """One batch for one language. Returns how much progress was made."""
    extra = await _remote_words(client, lang)
    async with async_session() as db:
        words = await gather_candidates(db, lang, batch_size(), extra)

    stats = STATE["languages"].setdefault(lang, {"indexed": 0, "no_entry": 0, "complete": False, "last_word": None})
    if not words:
        stats["complete"] = True
        return 0
    stats["complete"] = False

    found, missed, limited = [], [], False
    for word in words:
        status, entry = await fetch_entry(client, lang, word)
        stats["last_word"] = word
        if status == "ok":
            found.append(entry)
        elif status == "miss":
            missed.append(word)
        elif status == "rate":
            limited = True
            print(f"Dictionary seeder [{lang}]: rate limited, backing off")
            await asyncio.sleep(120)
            break
        await asyncio.sleep(60.0 / per_minute())

    saved = await persist_batch(lang, found, missed)
    stats["indexed"] += saved
    stats["no_entry"] += len(missed)
    STATE["last_batch_at"] = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    print(f"Dictionary seeder [{lang}]: indexed {saved}, no entry for {len(missed)} "
          f"(total indexed this run: {stats['indexed']})")
    return 1 if limited else saved + len(missed)


SCHEMA_STATEMENTS = [
    "ALTER TABLE IF EXISTS crawler.website_tokens ADD COLUMN IF NOT EXISTS kind VARCHAR(1) NOT NULL DEFAULT 'L'",
    "ALTER TABLE IF EXISTS crawler.website_characters ADD COLUMN IF NOT EXISTS kind VARCHAR(1) NOT NULL DEFAULT 'L'",
    "ALTER TABLE IF EXISTS crawler.website_characters ALTER COLUMN character TYPE VARCHAR(8)",
    "ALTER TABLE IF EXISTS search.dictionary_lexical_tokens ADD COLUMN IF NOT EXISTS kind VARCHAR(1) NOT NULL DEFAULT 'L'",
    "ALTER TABLE IF EXISTS search.dictionary_letter_index ADD COLUMN IF NOT EXISTS kind VARCHAR(1) NOT NULL DEFAULT 'L'",
    "ALTER TABLE IF EXISTS search.dictionary_grid_entries ADD COLUMN IF NOT EXISTS grid_columns SMALLINT",
]


async def ensure_schema() -> None:
    """Make sure the newer columns exist. Each step has its own transaction and is logged."""
    for statement in SCHEMA_STATEMENTS:
        try:
            async with engine.begin() as connection:
                await connection.execute(text(statement))
        except Exception as exc:
            print(f"Schema step failed: {type(exc).__name__}: {str(exc)[:160]} [{statement[:80]}]")
    print("Schema check finished.")


def log_source_configuration() -> None:
    sources = {
        "web results (SCRAPINGBEE_API_KEY)": bool(os.getenv("SCRAPINGBEE_API_KEY", "").strip()),
        "news (GNEWS_API_KEY)": bool(os.getenv("GNEWS_API_KEY", "").strip()),
    }
    for name, on in sources.items():
        print(f"Search source {name}: {'on' if on else 'OFF - set the variable on Render to enable it'}")


async def _acquire_lock():
    """Hold a database advisory lock so only one instance seeds at a time."""
    try:
        connection = await engine.connect()
        got = (await connection.execute(text("SELECT pg_try_advisory_lock(:key)"), {"key": LOCK_KEY})).scalar()
        await connection.commit()
        if got:
            return connection
        await connection.close()
    except Exception as exc:
        print(f"Dictionary seeder: could not take the lock ({type(exc).__name__})")
    return None


async def run_dictionary_seeder() -> None:
    """Started once at app boot. Never raises; logs everything it does."""
    STATE["enabled"] = enabled()
    log_source_configuration()
    try:
        await ensure_schema()
    except Exception as exc:
        print(f"Schema check skipped: {exc}")
    if not enabled():
        print("Dictionary seeder disabled (DICTIONARY_SEED_ENABLED).")
        return
    languages = seed_languages()
    if not languages:
        print("Dictionary seeder: no supported languages configured.")
        return

    await asyncio.sleep(20)  # let the app finish starting first
    lock = await _acquire_lock()
    if lock is None:
        print("Dictionary seeder: another instance is seeding; this one will not.")
        return

    STATE["running"] = True
    print(f"Dictionary seeder started for {', '.join(languages)} at {per_minute()} requests/minute.")
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=4.0),
            headers={"User-Agent": "LOMINII-dictionary-seeder/1.0"},
        ) as client:
            while True:
                progress = 0
                for lang in languages:
                    try:
                        progress += await seed_language(client, lang)
                    except asyncio.CancelledError:
                        raise
                    except Exception as exc:
                        STATE["last_error"] = f"{type(exc).__name__}: {str(exc)[:200]}"
                        print(f"Dictionary seeder [{lang}] error: {STATE['last_error']}")
                await asyncio.sleep(5 if progress else idle_seconds())
    finally:
        STATE["running"] = False
        try:
            await lock.close()
        except Exception:
            pass
