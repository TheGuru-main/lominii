"""
LOMINII GSP — Grid Placement and Elastic Cloud.

Keyboard layouts, tokenizer recognition, and placement-grid
coordinates are separate architectural components.
"""

import unicodedata

from lominii_platform.keymaps.registry import get_keyboard


GRID_COLUMNS = 56
GRID_ROWS = 64
REPLICA_COUNT = 5
REPLICA_ROW_STEP = 8

_DIGITS_ROW = "0123456789"


def get_keymap(lang: str = "en") -> dict:
    """
    Return keyboard character coordinates as (row, column).

    Keyboard coordinates are not the same as placement-grid
    coordinates. Digits retain their existing virtual positions.
    """
    rows = get_keyboard(lang)
    keymap = {}

    for row_index, row in enumerate(rows):
        for column_index, character in enumerate(row):
            keymap[character] = (row_index, column_index)

    for column_index, character in enumerate(_DIGITS_ROW):
        keymap[character] = (3, 26 + column_index)

    return keymap


def normalise(text: str, lang: str = "en") -> str:
    """
    Normalize text for the existing GSP helper functions.

    English receives lowercase conversion, diacritic removal,
    and light suffix stripping. Other languages retain accents.
    """
    text = text.lower()

    if lang == "en":
        text = "".join(
            character
            for character in unicodedata.normalize("NFKD", text)
            if not unicodedata.combining(character)
        )

        for suffix in ("ing", "ed", "s", "ly", "ment", "ness"):
            if text.endswith(suffix) and len(text) > len(suffix) + 2:
                text = text[:-len(suffix)]
                break

    return text


def calculate_lsum(word: str, lang: str = "en") -> int:
    """Sum keyboard row indices for recognized characters."""
    keymap = get_keymap(lang)
    return sum(keymap[character][0] for character in word if character in keymap)


def calculate_ssum(word: str, lang: str = "en") -> int:
    """Sum keyboard column indices for recognized characters."""
    keymap = get_keymap(lang)
    return sum(keymap[character][1] for character in word if character in keymap)


def first_letter_index(word: str, lang: str = "en") -> int:
    """Return the keyboard column index of the first character."""
    if not word:
        return 0

    character = word[0].lower()
    keymap = get_keymap(lang)

    if character in keymap:
        return keymap[character][1]

    return 0


def gsp_place(
    Lsum: int,
    Ssum: int,
    c: int,
    K: int = REPLICA_COUNT,
    D: int = REPLICA_ROW_STEP,
    C: int = GRID_COLUMNS,
    R: int = GRID_ROWS,
) -> dict:
    """
    Calculate the primary placement and replica cells.

    Existing placement equation:
        start_row = ((Lsum + Ssum - 1) % R) + 1
        row(k) = ((start_row - 1 + k * D) % R) + 1
        col(k) = (c + k) % C
    """
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

        cells.append({
            "col": column,
            "row": row,
            "k": k,
        })

    return {
        "start_row": start_row,
        "primary_cell": cells[0] if cells else None,
        "cells": cells,
    }


def elastic_cloud(
    L: int,
    S: int,
    c: int,
    radius: int = 1,
    first_letter_radius: int = 1,
    C: int = GRID_COLUMNS,
    R: int = GRID_ROWS,
) -> list:
    """Return neighboring placement cells for tolerant retrieval."""
    if C < 1 or R < 1:
        raise ValueError("Grid dimensions must be positive")

    cloud = set()

    for dc in range(-first_letter_radius, first_letter_radius + 1):
        column = (c + dc) % C

        for dL in range(-radius, radius + 1):
            for dS in range(-radius, radius + 1):
                if dL == 0 and dS == 0 and dc == 0:
                    continue

                start_row = ((L + dL + S + dS - 1) % R) + 1
                cloud.add((column, start_row))

    base_row = ((L + S - 1) % R) + 1
    cloud.add((c % C, base_row))

    return [
        {"col": column, "row": row}
        for column, row in sorted(cloud)
    ]
