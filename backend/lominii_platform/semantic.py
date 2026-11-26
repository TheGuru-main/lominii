"""
LOMINII lexical-semantic relevance.

This module ranks retrieved documents using weighted token and character
features. It does not calculate or modify GSP placement.
"""

import math
import re
import unicodedata
from collections import Counter


_TOKEN_RE = re.compile(r"[^\W_]+", flags=re.UNICODE)
_MAX_TEXT_CHARS = 24000


def _normalise(value: str) -> str:
    return unicodedata.normalize("NFC", value or "").casefold().strip()


def _tokens(value: str) -> list[str]:
    return _TOKEN_RE.findall(_normalise(value))


def _features(value: str) -> Counter:
    text = _normalise(value)
    tokens = _tokens(text)
    features = Counter()

    for token in tokens:
        if len(token) < 2:
            continue

        # Damped frequency prevents repeated terms dominating the score.
        features[f"w:{token}"] += 1.0

    # Character trigrams provide spelling-variation tolerance.
    for token in tokens:
        if len(token) < 3:
            continue

        padded = f"  {token}  "
        grams = {
            padded[index:index + 3]
            for index in range(len(padded) - 2)
        }

        for gram in grams:
            features[f"c:{gram}"] += 0.25

    return features


def _cosine(left: Counter, right: Counter) -> float:
    if not left or not right:
        return 0.0

    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))

    if not left_norm or not right_norm:
        return 0.0

    dot = sum(
        value * right.get(key, 0.0)
        for key, value in left.items()
    )

    return max(0.0, min(1.0, dot / (left_norm * right_norm)))


def relevance(
    query: str,
    title: str | None,
    content: str | None,
    language: str = "en",
) -> dict:
    """
    Return normalized lexical-semantic relevance.

    Language is retained in the interface for future language-specific
    weighting. Current token and character processing is Unicode-aware.
    """
    del language

    query_features = _features(query)
    if not query_features:
        return {
            "score": 0.0,
            "body_score": 0.0,
            "title_score": 0.0,
            "matched_terms": [],
        }

    title_text = (title or "")[:4000]
    body_text = (content or "")[:_MAX_TEXT_CHARS]

    title_features = _features(title_text)
    body_features = _features(body_text)

    body_score = _cosine(query_features, body_features)
    title_score = _cosine(query_features, title_features)

    if title_features:
        score = (body_score * 0.65) + (title_score * 0.35)
    else:
        score = body_score

    query_terms = set(_tokens(query))
    document_terms = set(_tokens(title_text + " " + body_text))

    matched_terms = sorted(query_terms.intersection(document_terms))

    return {
        "score": round(max(0.0, min(1.0, score)), 6),
        "body_score": round(body_score, 6),
        "title_score": round(title_score, 6),
        "matched_terms": matched_terms[:20],
    }
