"""
Gurutech Scatter Protocol – Core Placement & Elastic Cloud (Platform Layer)
Multi‑language support: English (QWERTY), French (AZERTY), German (QWERTZ),
Arabic (standard 101‑key), Chinese (Pinyin virtual map).
"""

import unicodedata

# ============================================================================
# 1. MULTI‑LANGUAGE KEYBOARD MAPS  (36‑column: a‑z + 0‑9)ENGLISH,FRENCH,ARABIC,CHINESE,GERMAN,...
# ============================================================================
# Each language map defines the letters a‑z on rows 0‑2.
# Digits 0‑9 are always on row 3, columns 26‑35.
# The GSP formula never changes – only the starting table.

_KEYMAPS = {
    "en": [                     # English QWERTY
        "qwertyuiop",
        "asdfghjkl",
        "zxcvbnm"
    ],
    "fr": [                     # French AZERTY
        "azertyuiop",
        "qsdfghjklm",
        "wxcvbn"
    ],
    "de": [                     # German QWERTZ
        "qwertzuiop",
        "asdfghjkl",
        "yxcvbnm"
    ],
    "ar": [                     # Arabic (standard 101‑key)
        "ضصثقفغعهخح",
        "شسيبلاتنمك",
        "ئءؤرلاىةوز"
    ],
    "zh": [                     # Chinese – Pinyin virtual map
        # The 26 most common Pinyin initials (first row) and finals (second row)
        # Row 0: initials  b,p,m,f,d,t,n,l,g,k,h,j,q,x,zh,ch,sh,r,z,c,s,y,w
        "bpmfdtnlgkhjqxz",
        # Row 1: common finals  a,o,e,i,u,ü,ai,ei,ao,ou,an,en,ang,eng,ong,ia,ie,iu,ian,in,ing,ua,uo,uai,ui,uan,un,uang,iong
        "aoeiuüaieiaoouan",
        "enangengongiaiei"
    ]
}

_DIGITS_ROW = "0123456789"


def get_keymap(lang: str = "en") -> dict:
    """Return a dict mapping character -> (L, S) for the given language."""
    rows = _KEYMAPS.get(lang, _KEYMAPS["en"])
    km = {}
    for r, row in enumerate(rows):
        for c, ch in enumerate(row):
            km[ch] = (r, c)
    # Add digits (row 3, columns 26‑35)
    for c, ch in enumerate(_DIGITS_ROW):
        km[ch] = (3, 26 + c)
    return km


# ============================================================================
# 2. LANGUAGE‑AWARE NORMALISATION
# ============================================================================
def normalise(text: str, lang: str = "en") -> str:
    """Normalise text for the given language.
    English: lower, strip diacritics, light stemming.
    Other languages: lower only (never remove accents or stem).
    """
    text = text.lower()
    if lang == "en":
        # Remove diacritics (e.g., café → cafe)
        text = ''.join(c for c in unicodedata.normalize('NFKD', text)
                       if not unicodedata.combining(c))
        # Light stemming – strip common suffixes
        for suffix in ('ing', 'ed', 's', 'ly', 'ment', 'ness'):
            if text.endswith(suffix) and len(text) > len(suffix) + 2:
                text = text[:-len(suffix)]
                break
    return text


# ================================================
# 3. GSP FUNCTIONS (Language‑aware)
# ===============================================
def calculate_lsum(word: str, lang: str = "en") -> int:
    """Sum of row indices of each character in the word."""
    km = get_keymap(lang)
    return sum(km[ch][0] for ch in word if ch in km)


def calculate_ssum(word: str, lang: str = "en") -> int:
    """Sum of column indices of each character in the word."""
    km = get_keymap(lang)
    return sum(km[ch][1] for ch in word if ch in km)


def first_letter_index(word: str, lang: str = "en") -> int:
    """Column index (0‑35) of the first character in the word."""
    if not word:
        return 0
    ch = word[0].lower()
    km = get_keymap(lang)
    if ch in km:
        return km[ch][1]          # column index
    # Fallback for characters not in the keymap
    return 0


# ============================================================================
# 4. CORE PLACEMENT (unchanged) ========================================================
def gsp_place(Lsum: int, Ssum: int, c: int, K: int = 5, D: int = 8,
              C: int = 26, R: int = 64) -> dict:
    """Return start_row, primary_cell, and all K cells for the given parameters."""
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


# ============================================================================
# 5. ELASTIC CLOUD (unchanged)
# ============================================================================
def elastic_cloud(L: int, S: int, c: int, radius: int = 1,
                  first_letter_radius: int = 1, C: int = 26, R: int = 64) -> list:
    """Return a list of neighbouring cells for typo‑tolerant search."""
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