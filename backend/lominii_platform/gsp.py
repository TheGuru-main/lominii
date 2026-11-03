"""LOMINII GSP — deterministic query placement and elastic retrieval cells.

Grid face
  * Letter face (face "L"): columns = length of the selected language's
    alphabet (en 26, fr 26, de 30, yo 25, ha 28, ig 36), rows = 64.
  * Number face (face "N"): queries made only of digits use a separate
    10-column face, so numbers are never placed as if they were letters.
  * Face "X": nothing placeable (empty, punctuation or foreign-only text);
    deterministic fallback cell, never indexed.

L = number of letter tokens, uID = ordered zero-based alphabet indices of the
letter tokens, S = sum(uID), c = index of the first letter token.
Digits never enter L, S or c of a letter query; they travel separately as the
number chain.
"""
from lominii_platform.keymaps.keyboard import (
    DEFAULT_LANGUAGE,
    NUMBER_FACE_COLUMNS,
    alphabet_index_map,
    calculate_number_chain,
    calculate_uid_chain as _uid_chain,
    get_keyboard,
    grid_columns,
    normalise_text,
    tokenize,
)

GRID_ROWS = 64
REPLICA_COUNT = 5
REPLICA_ROW_STEP = 8
# English face. Kept only so older imports keep working; new code must pass
# grid_columns(lang) (or use place_text) instead of relying on this default.
GRID_COLUMNS = grid_columns(DEFAULT_LANGUAGE)
_DIGITS_ROW = "0123456789"


def get_keymap(lang: str = "en") -> dict:
    """Return keyboard coordinates as (row, column), separate from GSP values."""
    keymap = {}
    for row_index, row in enumerate(get_keyboard(lang)):
        for column_index, character in enumerate(row.lower()):
            keymap[character] = (row_index, column_index)
    for column_index, character in enumerate(_DIGITS_ROW):
        keymap[character] = (3, 26 + column_index)
    return keymap


def normalise(text: str, lang: str = "en") -> str:
    """NFC + lowercase + trim. Accents are folded by the tokenizer, not here."""
    return normalise_text(text)


def calculate_uid_chain(word: str, lang: str = "en") -> list[int]:
    """Ordered zero-based alphabet indices of the letter tokens."""
    return _uid_chain(word, lang)


def calculate_lsum(word: str, lang: str = "en") -> int:
    """L is the number of letter tokens (a digraph such as 'gb' counts once)."""
    return len(calculate_uid_chain(word, lang))


def calculate_ssum(word: str, lang: str = "en") -> int:
    """S is the sum of the letter tokens' alphabet indices."""
    return sum(calculate_uid_chain(word, lang))


def first_letter_index(word: str, lang: str = "en") -> int:
    """Alphabet index of the first letter token (0 when there is none)."""
    chain = calculate_uid_chain(word, lang)
    return chain[0] if chain else 0


def keyboard_column_index(word: str, lang: str = "en") -> int:
    """Physical keyboard column of the first letter token (display aid only)."""
    tokens = [t for t in tokenize(word, lang) if t.kind == "L"]
    if not tokens:
        return 0
    first = tokens[0]
    for row in get_keyboard(lang):
        position = row.find(first.value[0])
        if position >= 0:
            return position
    # Letters typed from the extra row have no QWERTY column.
    return first.index % grid_columns(lang)


def query_marker(word: str, lang: str = "en") -> dict:
    """Tokenizer marker: which grid face a text uses and its GSP inputs."""
    tokens = tokenize(word, lang)
    letters = [t.index for t in tokens if t.kind == "L"]
    numbers = [t.index for t in tokens if t.kind == "N"]
    if letters:
        face, columns = "L", grid_columns(lang)
        L, S, c = len(letters), sum(letters), letters[0]
    elif numbers:
        face, columns = "N", NUMBER_FACE_COLUMNS
        L, S, c = len(numbers), sum(numbers), numbers[0]
    else:
        face, columns = "X", grid_columns(lang)
        L = S = c = 0
    return {
        "lang": (lang or DEFAULT_LANGUAGE).lower().split("-", 1)[0],
        "face": face,
        "columns": columns,
        "L": L,
        "S": S,
        "c": c,
        "uid": letters,
        "numbers": numbers,
    }


def gsp_place(Lsum: int, Ssum: int, c: int, K: int = REPLICA_COUNT,
              D: int = REPLICA_ROW_STEP, C: int | None = None,
              R: int = GRID_ROWS) -> dict:
    """Calculate primary and replica cells using the established GSP equations.

    C is the number of grid columns for the face in use. When omitted the
    English face is used; callers that know the language must pass it.
    """
    if C is None:
        C = GRID_COLUMNS
    if C < 1 or R < 1:
        raise ValueError("Grid dimensions must be positive")
    if K < 1:
        raise ValueError("Replica count must be at least 1")
    start_row = ((Lsum + Ssum - 1) % R) + 1
    start_column = c % C
    cells = []
    for k in range(K):
        row = ((start_row - 1 + k * D) % R) + 1
        column = (start_column + k) % C
        cells.append({"col": column, "row": row, "k": k})
    return {"start_row": start_row, "primary_cell": cells[0], "cells": cells,
            "columns": C}


def place_text(word: str, lang: str = "en", K: int = REPLICA_COUNT,
               D: int = REPLICA_ROW_STEP, R: int = GRID_ROWS) -> dict:
    """Tokenize text and place it on the correct face for its language."""
    marker = query_marker(word, lang)
    placement = gsp_place(marker["L"], marker["S"], marker["c"],
                          K=K, D=D, C=marker["columns"], R=R)
    placement["marker"] = marker
    return placement


def elastic_cloud(L: int, S: int, c: int, radius: int = 1,
                  first_letter_radius: int = 1, C: int | None = None,
                  R: int = GRID_ROWS) -> list:
    """Return neighboring cells around the GSP placement.

    c must be the same value used for placement (alphabet index), so the
    cloud always contains the primary cell.
    """
    if C is None:
        C = GRID_COLUMNS
    if C < 1 or R < 1:
        raise ValueError("Grid dimensions must be positive")
    if radius < 0 or first_letter_radius < 0:
        raise ValueError("Elastic-cloud radii cannot be negative")
    cloud = set()
    for dc in range(-first_letter_radius, first_letter_radius + 1):
        column = (c + dc) % C
        for dL in range(-radius, radius + 1):
            for dS in range(-radius, radius + 1):
                row = ((L + dL + S + dS - 1) % R) + 1
                cloud.add((column, row))
    return [{"col": col, "row": row} for col, row in sorted(cloud)]
