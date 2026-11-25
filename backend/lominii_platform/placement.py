"""
Placement Source Interface (Platform Layer)
Every placement family now includes a namespace identifier.
"""

from abc import ABC, abstractmethod
from .gsp import (
    GRID_COLUMNS,
    calculate_lsum,
    calculate_ssum,
    first_letter_index,
    gsp_place,
    query_marker,
)
from .gsg import gps_to_gsg, GSG_COLS
from .nsid import NSID
import hashlib


class PlacementSource(ABC):
    """Abstract base for all GSP placement families."""

    @abstractmethod
    def identity_inputs(self) -> dict:
        """Return the raw inputs that define this placement."""
        ...

    @abstractmethod
    def parameters(self) -> dict:
        """Return K, D, C, R, and any other placement parameters."""
        ...

    @abstractmethod
    def namespace_id(self) -> int:
        """Return the NSID for this placement family."""
        ...

    def compute(self):
        """Execute gsp_place with the configured parameters."""
        params = self.parameters()
        L = params["L"]
        S = params["S"]
        c = params["c"]
        K = params.get("K", 5)
        D = params.get("D", 8)
        C = params.get("C", GRID_COLUMNS)
        R = params.get("R", 64)
        return gsp_place(L, S, c, K=K, D=D, C=C, R=R)


class KeyboardPlacement(PlacementSource):
    """Placement based on a word or name (keyboard geometry)."""

    def __init__(self, word: str, K: int = 5, D: int = 8, lang: str = "en", nsid: int = None):
        self.word = word
        self._K = K
        self._D = D
        self.lang = lang
        self._nsid = nsid if nsid is not None else NSID.SEARCH

    def identity_inputs(self) -> dict:
        return {"word": self.word, "language": self.lang}

    def parameters(self) -> dict:
        marker = query_marker(self.word, self.lang)
        return {"L": marker["L"], "S": marker["S"], "c": marker["c"],
                "C": marker["columns"], "K": self._K, "D": self._D}

    def namespace_id(self) -> int:
        return self._nsid


class GSGPlacement(PlacementSource):
    """Placement based on GPS coordinates (Guru Spatial Grid)."""

    def __init__(self, lat: float, lon: float, K: int = 5, D: int = 8, nsid: int = None):
        self.lat = lat
        self.lon = lon
        self._K = K
        self._D = D
        self._nsid = nsid if nsid is not None else NSID.SHOP

    def identity_inputs(self) -> dict:
        return {"latitude": self.lat, "longitude": self.lon}

    def parameters(self) -> dict:
        (gsg_x, gsg_y), (L, S, c) = gps_to_gsg(self.lat, self.lon)
        return {"L": L, "S": S, "c": c, "C": GSG_COLS, "K": self._K, "D": self._D,
                "gsg_cell": (gsg_x, gsg_y)}

    def namespace_id(self) -> int:
        return self._nsid


CRAWLER_K = 250
CRAWLER_D = 8
CRAWLER_PHASES = ("word", "text")


class CrawlerPlacement(PlacementSource):
    """Crawler placement inputs, separate from user placement.

    Only words and full text are calculated and placed.
    L = word length (word) or text length (text, spaces excluded).
    S = sum of the 0-based letter-index chain, c = its first index.
    Letters are never calculated: a letter is only its 0-based index marker.
    Pass normalised text, as for every other GSP placement.
    """

    def __init__(self, text: str, lang: str = "en", phase: str = "word"):
        if phase not in CRAWLER_PHASES:
            raise ValueError("phase must be word or text")
        self.text = text
        self.lang = lang
        self.phase = phase
        self._K = CRAWLER_K
        self._D = CRAWLER_D

    def identity_inputs(self) -> dict:
        return {"text": self.text, "language": self.lang, "phase": self.phase}

    def parameters(self) -> dict:
        marker = query_marker(self.text, self.lang)
        chain = list(marker["uid"] or marker["numbers"])
        length = len("".join(self.text.split())) if self.phase == "text" else len(chain)
        return {"L": length, "S": sum(chain), "c": chain[0] if chain else 0,
                "C": marker["columns"], "K": self._K, "D": self._D,
                "face": marker["face"]}

    def namespace_id(self) -> int:
        return NSID.CRAWLER
