"""LOMINII GSP — deterministic query placement and elastic retrieval cells.

L = number of ASCII alphabet letters; uID = ordered zero-based alphabet indices;
S = sum(uID); c = first letter's column on the selected language keyboard.
"""
import unicodedata
from lominii_platform.keymaps.registry import get_keyboard

GRID_COLUMNS = 56
GRID_ROWS = 64
REPLICA_COUNT = 5
REPLICA_ROW_STEP = 8
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
    """Lowercase and fold diacritics without stemming or deleting query words."""
    text = unicodedata.normalize("NFKD", (text or "").lower())
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def calculate_uid_chain(word: str, lang: str = "en") -> list[int]:
    """Return ordered zero-based alphabet indices for a-z in the normalized query."""
    normalized = normalise(word, lang)
    return [ord(ch) - ord("a") for ch in normalized if "a" <= ch <= "z"]


def calculate_lsum(word: str, lang: str = "en") -> int:
    """Return L: letter count, not keyboard-row coordinates."""
    return len(calculate_uid_chain(word, lang))


def calculate_ssum(word: str, lang: str = "en") -> int:
    """Return S: sum of the ordered zero-based alphabet-index chain."""
    return sum(calculate_uid_chain(word, lang))


def first_letter_index(word: str, lang: str = "en") -> int:
    """Return the keyboard column of the first alphabet letter for this language."""
    normalized = normalise(word, lang)
    character = next((ch for ch in normalized if "a" <= ch <= "z"), "")
    if not character:
        return 0
    return get_keymap(lang).get(character, (0, 0))[1]


def gsp_place(Lsum: int, Ssum: int, c: int, K: int = REPLICA_COUNT,
              D: int = REPLICA_ROW_STEP, C: int = GRID_COLUMNS,
              R: int = GRID_ROWS) -> dict:
    """Calculate primary and replica cells using the established GSP equations."""
    if C < 1 or R < 1:
        raise ValueError("Grid dimensions must be positive")
    if K < 0:
        raise ValueError("Replica count cannot be negative")
    start_row = ((Lsum + Ssum - 1) % R) + 1
    start_column = c % C
    cells = []
    for k in range(K):
        row = ((start_row - 1 + k * D) % R) + 1
        column = (start_column + k) % C
        cells.append({"col": column, "row": row, "k": k})
    return {"start_row": start_row, "primary_cell": cells[0] if cells else None, "cells": cells}


def elastic_cloud(L: int, S: int, c: int, radius: int = 1,
                  first_letter_radius: int = 1, C: int = GRID_COLUMNS,
                  R: int = GRID_ROWS) -> list:
    """Return neighboring cells around the corrected GSP placement."""
    if C < 1 or R < 1:
        raise ValueError("Grid dimensions must be positive")
    if radius < 0 or first_letter_radius < 0:
        raise ValueError("Elastic-cloud radii cannot be negative")
    cloud = set()
    for dc in range(-first_letter_radius, first_letter_radius + 1):
        column = (c + dc) % C
        for dL in range(-radius, radius + 1):
            for dS in range(-radius, radius + 1):
                if dL == 0 and dS == 0 and dc == 0:
                    continue
                row = ((L + dL + S + dS - 1) % R) + 1
                cloud.add((column, row))
    base_row = ((L + S - 1) % R) + 1
    cloud.add((c % C, base_row))
    return [{"col": col, "row": row} for col, row in sorted(cloud)]
