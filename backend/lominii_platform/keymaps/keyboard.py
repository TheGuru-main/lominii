"""
LOMINII language alphabets, tokenizer and keyboard layouts.

Single source of truth for:
  * each language's official alphabet (order defines uID, length defines the
    GSP grid column count for that language),
  * the physical keyboard rows (single characters only; digraph letters such
    as "gb" or "sh" are typed as two keys and tokenized as ONE letter),
  * the tokenizer, which marks every unit as a Letter (L), Number (N) or
    Foreign letter (F).

Token kinds
  L  letter of the selected language's alphabet; index = position in alphabet
  N  decimal digit; index = its value 0-9. Never shares an index space with
     letters, so a number can never be mistaken for a letter.
  F  alphabetic character that is not in the selected alphabet (for example
     "c" in Yoruba or a Cyrillic letter). Kept for indexing, never placed.
Everything else (spaces, punctuation, symbols) is dropped.
"""

from __future__ import annotations

import unicodedata
from functools import lru_cache
from typing import NamedTuple

# --------------------------------------------------------------------------
# Alphabets. Digraph letters are single entries ("gb", "sh", ...).
# Order = uID order. len(ALPHABETS[code]) = GSP grid columns for that language.
# --------------------------------------------------------------------------
_LATIN = tuple("abcdefghijklmnopqrstuvwxyz")

ALPHABETS: dict[str, tuple[str, ...]] = {
    "en": _LATIN,                                   # 26
    "fr": _LATIN,                                   # 26 (accents fold to base)
    "de": _LATIN + ("ä", "ö", "ü", "ß"),            # 30
    "yo": (                                         # 25
        "a", "b", "d", "e", "ẹ", "f", "g", "gb", "h", "i", "j", "k", "l",
        "m", "n", "o", "ọ", "p", "r", "s", "ṣ", "t", "u", "w", "y",
    ),
    "ha": (                                         # 28 (Boko)
        "a", "b", "ɓ", "c", "d", "ɗ", "e", "f", "g", "h", "i", "j", "k", "ƙ",
        "l", "m", "n", "o", "r", "s", "sh", "t", "ts", "u", "w", "y", "ƴ", "z",
    ),
    "ig": (                                         # 36 (Ọnwụ)
        "a", "b", "ch", "d", "e", "f", "g", "gb", "gh", "gw", "h", "i", "ị",
        "j", "k", "kp", "kw", "l", "m", "n", "ṅ", "nw", "ny", "o", "ọ", "p",
        "r", "s", "sh", "t", "u", "ụ", "v", "w", "y", "z",
    ),
}

# Physical keyboard rows: single characters only (no digraphs).
KEYBOARDS: dict[str, tuple[str, ...]] = {
    "en": ("qwertyuiop", "asdfghjkl", "zxcvbnm"),
    "fr": ("azertyuiop", "qsdfghjklm", "wxcvbn"),
    "de": ("qwertzuiop", "asdfghjkl", "yxcvbnm"),
    "yo": ("wertyuiop", "asdfghjkl", "bnm"),
    "ha": ("wertyuio", "asdfghjkl", "zcbnm"),
    "ig": ("wertyuiop", "asdfghjkl", "zvbnm"),
}

# Extra single-character keys shown on an additional row.
EXTRA_KEYS: dict[str, tuple[str, ...]] = {
    "en": (),
    "fr": (),
    "de": ("ä", "ö", "ü", "ß"),
    "yo": ("ẹ", "ọ", "ṣ"),
    "ha": ("ɓ", "ɗ", "ƙ", "ƴ"),
    "ig": ("ị", "ọ", "ụ", "ṅ"),
}

# Digraph keys that cannot be typed from the letter rows of that layout
# (Igbo has no standalone "c", so "ch" needs its own key).
DIGRAPH_KEYS: dict[str, tuple[str, ...]] = {"ig": ("ch",)}

LANGUAGE_NAMES = {
    "en": "English", "fr": "French", "de": "German",
    "yo": "Yoruba", "ha": "Hausa", "ig": "Igbo",
}

SUPPORTED_LANGUAGES = frozenset(ALPHABETS)
DEFAULT_LANGUAGE = "en"
NUMBER_FACE_COLUMNS = 10          # digits 0-9: the numeric face of the grid

# Combining marks that are part of a language's letters and must survive
# decomposition (dot below in ẹ ọ ṣ ị ụ, dot above in ṅ). Tone marks are not.
_KEEP_MARKS = {
    "yo": {"\u0323"},
    "ig": {"\u0323", "\u0307"},
}

# Folds applied to characters that are not letters of the language.
_SPECIAL_FOLD = {
    "œ": "oe", "æ": "ae", "ß": "ss", "ø": "o", "ł": "l", "đ": "d",
    "ð": "d", "þ": "th", "ı": "i",
}


class Token(NamedTuple):
    kind: str      # "L", "N" or "F"
    value: str     # letter text as in the alphabet ("gb"), digit, or foreign char
    index: int     # L: alphabet index, N: digit value 0-9, F: -1


def _code(language: str | None) -> str:
    code = (language or DEFAULT_LANGUAGE).lower().split("-", 1)[0]
    return code if code in ALPHABETS else DEFAULT_LANGUAGE


def normalise_text(text: str) -> str:
    """NFC + lowercase + trim. Accents are kept here and folded when tokenizing."""
    return unicodedata.normalize("NFC", (text or "").strip().lower())


def get_alphabet(language: str = "en") -> tuple[str, ...]:
    return ALPHABETS[_code(language)]


def alphabet_length(language: str = "en") -> int:
    return len(get_alphabet(language))


def grid_columns(language: str = "en") -> int:
    """GSP grid column count for a language = length of its alphabet."""
    return alphabet_length(language)


def get_keyboard(language: str = "en") -> list[str]:
    return list(KEYBOARDS[_code(language)])


@lru_cache(maxsize=None)
def alphabet_index_map(language: str = "en") -> dict[str, int]:
    return {letter: i for i, letter in enumerate(get_alphabet(language))}


@lru_cache(maxsize=None)
def _single_letters(code: str) -> frozenset[str]:
    return frozenset(x for x in ALPHABETS[code] if len(x) == 1)


@lru_cache(maxsize=None)
def _digraphs(code: str) -> frozenset[str]:
    return frozenset(x for x in ALPHABETS[code] if len(x) == 2)


def _fold_char(ch: str, code: str) -> str:
    """Fold one character to letters of the language where possible."""
    letters = _single_letters(code)
    if ch in letters:
        return ch
    decomposed = unicodedata.normalize("NFD", ch)
    if len(decomposed) > 1:
        keep = _KEEP_MARKS.get(code, set())
        kept = "".join(m for m in decomposed[1:] if m in keep)
        composed = unicodedata.normalize("NFC", decomposed[0] + kept)
        if composed in letters:
            return composed
        if decomposed[0] in letters:
            return decomposed[0]
        ch = decomposed[0]
    return _SPECIAL_FOLD.get(ch, ch)


def tokenize(text: str, language: str = "en") -> list[Token]:
    """
    Split text into L / N / F tokens for a language.

    Digraph letters (gb, sh, ch ...) are matched greedily and never across a
    space or punctuation mark. Digits (any script) become N tokens.
    """
    code = _code(language)
    letters = _single_letters(code)
    digraphs = _digraphs(code)
    index = alphabet_index_map(code)

    # Fold into units; None marks a separator that blocks digraph matching.
    units: list[str | None] = []
    for ch in normalise_text(text):
        folded = _fold_char(ch, code)
        for part in folded:
            if part in letters or part.isalpha() or unicodedata.decimal(part, None) is not None:
                units.append(part)
            else:
                units.append(None)

    tokens: list[Token] = []
    i = 0
    while i < len(units):
        unit = units[i]
        if unit is None:
            i += 1
            continue
        nxt = units[i + 1] if i + 1 < len(units) else None
        if nxt is not None and (unit + nxt) in digraphs:
            tokens.append(Token("L", unit + nxt, index[unit + nxt]))
            i += 2
            continue
        if unit in letters:
            tokens.append(Token("L", unit, index[unit]))
        else:
            digit = unicodedata.decimal(unit, None)
            if digit is not None:
                tokens.append(Token("N", str(digit), digit))
            elif unit.isalpha():
                tokens.append(Token("F", unit, -1))
        i += 1
    return tokens


def calculate_uid_chain(text: str, language: str = "en") -> list[int]:
    """Alphabet indices of the letter tokens only, in input order."""
    return [t.index for t in tokenize(text, language) if t.kind == "L"]


def calculate_number_chain(text: str, language: str = "en") -> list[int]:
    """Digit values (0-9) of the number tokens only, in input order."""
    return [t.index for t in tokenize(text, language) if t.kind == "N"]


def word_kind(word: str, language: str = "en") -> str:
    """Kind of one word: N digits only, L letters only (foreign included), M mixed."""
    kinds = {("N" if t.kind == "N" else "L") for t in tokenize(word, language)}
    if kinds == {"N"}:
        return "N"
    if kinds == {"L"}:
        return "L"
    return "M" if kinds else "L"


# --------------------------------------------------------------------------
# Language recognition from alphabet evidence (works on short queries).
# Only letters unique to one language count; tone-marked é/è/à are NOT used,
# because Yoruba and Igbo text carries them too.
# --------------------------------------------------------------------------
_UNIQUE_MARKERS = {
    "yo": set("ẹṣ"),
    "ig": set("ịụṅ"),
    "ha": set("ɓɗƙƴ"),
    "de": set("äöüß"),
    "fr": set("çœæÿ"),
}
_SHARED_YO_IG = set("ọ")


def detect_by_alphabet(text: str) -> str | None:
    """Return a language when its distinctive letters appear, else None."""
    sample = normalise_text(text)
    scores = {
        code: sum(1 for ch in sample if ch in marks)
        for code, marks in _UNIQUE_MARKERS.items()
    }
    # Dot-below ọ counts for Yoruba or Igbo only when the other evidence agrees.
    if _SHARED_YO_IG & set(sample):
        for code in ("yo", "ig"):
            if scores[code]:
                scores[code] += sample.count("ọ")
    best = max(scores.values())
    if best == 0:
        return None
    winners = [code for code, score in scores.items() if score == best]
    return winners[0] if len(winners) == 1 else None


def detect_language(text: str, default: str = "en") -> str:
    """
    Alphabet evidence first (short queries), then langdetect for longer text,
    then the default. langdetect cannot return yo/ha/ig.
    """
    fallback = _code(default)
    by_alphabet = detect_by_alphabet(text)
    if by_alphabet:
        return by_alphabet

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
