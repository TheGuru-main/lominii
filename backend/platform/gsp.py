"""Gurutech Scatter Protocol – Core Placement & Elastic Cloud (Platform Layer)"""

import unicodedata

# ---------- Normalisation ----------

def normalise(text: str, lang: str = "en") -> str:
    text = text.lower()
    if lang == "en":
        # Remove diacritics (e.g., café → cafe)
        text = ''.join(c for c in unicodedata.normalize('NFKD', text) if not unicodedata.combining(c))
        # Lightweight stemming (strip common suffixes)
        for suffix in ('ing', 'ed', 's', 'ly', 'ment', 'ness'):
            if text.endswith(suffix) and len(text) > len(suffix) + 2:
                text = text[:-len(suffix)]
                break
    # For non‑English, only lowercase – never remove accents or stem
    return text

# ---------- Keyboard Mapping (LOMINII 36‑column) ----------

KEYBOARD_ROWS = ["qwertyuiop", "asdfghjkl", "zxcvbnm", "0123456789"]
keymap = {}
for r, row in enumerate(KEYBOARD_ROWS):
    for c, ch in enumerate(row):
        keymap[ch] = (r, c)

def calculate_lsum(word: str) -> int:
    return sum(keymap[ch][0] for ch in word if ch in keymap)

def calculate_ssum(word: str) -> int:
    return sum(keymap[ch][1] for ch in word if ch in keymap)

def first_letter_index(word: str) -> int:
    if not word:
        return 0
    ch = word[0].lower()
    if 'a' <= ch <= 'z':
        return ord(ch) - 97
    if '0' <= ch <= '9':
        return 26 + (ord(ch) - 48)
    return 0   # fallback

# ---------- Core Placement ----------

def gsp_place(Lsum: int, Ssum: int, c: int, K: int = 5, D: int = 8,
              C: int = 26, R: int = 64) -> dict:
    start_row = ((Lsum + Ssum - 1) % R) + 1
    cells = []
    for k in range(K):
        row = ((start_row - 1 + k * D) % R) + 1
        col = (c + k) % C
        cells.append({"col": col, "row": row, "k": k})
    return {
        "start_row": start_row,
        "primary_cell": cells[0] if cells else None,
        "cells": cells
    }

# ---------- Elastic Cloud ----------

def elastic_cloud(L: int, S: int, c: int, radius: int = 1,
                  first_letter_radius: int = 1, C: int = 26, R: int = 64) -> list:
    cloud = set()
    for dc in range(-first_letter_radius, first_letter_radius + 1):
        c2 = (c + dc) % C
        for dL in range(-radius, radius + 1):
            for dS in range(-radius, radius + 1):
                if dL == 0 and dS == 0 and dc == 0:
                    continue
                L2 = L + dL
                S2 = S + dS
                start_row = ((L2 + S2 - 1) % R) + 1
                cloud.add((c2, start_row))
    base_start_row = ((L + S - 1) % R) + 1
    cloud.add((c % C, base_start_row))
    return [{"col": col, "row": row} for col, row in cloud]