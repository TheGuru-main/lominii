"""
LOMINII language-aware keyboard and alphabet index rules.

Alphabet indices are zero-based and independent of physical key positions.
The same language rules must be used by the keyboard and search/GSP.
"""

from __future__ import annotations

import unicodedata
from functools import lru_cache


# Alphabet order defines uID. Keyboard rows define only key placement.
ALPHABETS = {
    "en": tuple("abcdefghijklmnopqrstuvwxyz"),
    "fr": tuple("abcdefghijklmnopqrstuvwxyz"),
    "de": tuple("abcdefghijklmnopqrstuvwxyz") + ("ä", "ö", "ü", "ß"),
    "yo": tuple("abcdefghijklmnopqrstuvwxyz") + ("ẹ", "ọ", "ṣ"),
    "ha": tuple("abcdefghijklmnopqrstuvwxyz") + ("ɓ", "ɗ", "ƙ", "ƴ"),
    "ig": tuple("abcdefghijklmnopqrstuvwxyz") + ("ị", "ọ", "ụ", "ṅ"),
}

KEYBOARDS = {
    "en": ("qwertyuiop", "asdfghjkl", "zxcvbnm"),
    "fr": ("azertyuiop", "qsdfghjklm", "wxcvbn"),
    "de": ("qwertzuiop", "asdfghjkl", "yxcvbnm"),
    "yo": ("qwertyuiop", "asdfghjkl", "zxcvbnm"),
    "ha": ("qwertyuiop", "asdfghjkl", "zxcvbnm"),
    "ig": ("qwertyuiop", "asdfghjkl", "zxcvbnm"),
}

LANGUAGE_NAMES = {
    "en": "English",
    "fr": "French",
    "de": "German",
    "yo": "Yoruba",
    "ha": "Hausa",
    "ig": "Igbo",
}

SUPPORTED_LANGUAGES = frozenset(ALPHABETS)


def normalise_text(text: str) -> str:
    """Unicode-normalise and lowercase without discarding language letters."""
    return unicodedata.normalize("NFC", (text or "").strip().lower())


def get_alphabet(language: str = "en") -> tuple[str, ...]:
    """Return the canonical, ordered alphabet for a language."""
    code = (language or "en").lower().split("-", 1)[0]
    return ALPHABETS.get(code, ALPHABETS["en"])


def get_keyboard(language: str = "en") -> list[str]:
    """Return physical keyboard rows, independently of alphabet indices."""
    code = (language or "en").lower().split("-", 1)[0]
    return list(KEYBOARDS.get(code, KEYBOARDS["en"]))


def alphabet_index_map(language: str = "en") -> dict[str, int]:
    """Map each alphabet symbol to its zero-based language-specific index."""
    return {letter: index for index, letter in enumerate(get_alphabet(language))}


def calculate_uid_chain(text: str, language: str = "en") -> list[int]:
    """
    Return alphabet indices in input order.
    Characters outside the selected alphabet are ignored, not reindexed.
    """
    indices = alphabet_index_map(language)
    normalized = normalise_text(text)
    return [indices[char] for char in normalized if char in indices]


def detect_language(text: str, default: str = "en") -> str:
    """
    Detect language when langdetect is installed.
    Short or ambiguous text safely uses the supplied/default language.
    """
    fallback = (default or "en").lower().split("-", 1)[0]
    if fallback not in SUPPORTED_LANGUAGES:
        fallback = "en"

    sample = (text or "").strip()
    if len(sample) < 20:
        return fallback

    try:
        from langdetect import DetectorFactory, detect
        DetectorFactory.seed = 0
        detected = detect(sample)
        return detected if detected in SUPPORTED_LANGUAGES else fallback
    except Exception:
        return fallback


@lru_cache(maxsize=1)
def language_detection_available() -> bool:
    try:
        import langdetect  # noqa: F401
        return True
    except ImportError:
        return False
