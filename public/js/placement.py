"""
Placement Source Interface (Platform Layer)

Defines the contract for all placement families.
Every placement source must provide:
    - identity inputs (what is being placed)
    - parameters (K, D, grid size)
    - compute() -> list of cells
"""

from abc import ABC, abstractmethod
from .gsp import (
    calculate_lsum,
    calculate_ssum,
    first_letter_index,
    gsp_place,
)
from .gsg import gps_to_gsg
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

    def compute(self):
        """Execute gsp_place with the configured parameters."""
        params = self.parameters()
        L = params["L"]
        S = params["S"]
        c = params["c"]
        K = params.get("K", 5)
        D = params.get("D", 8)
        C = params.get("C", 26)
        R = params.get("R", 64)
        return gsp_place(L, S, c, K=K, D=D, C=C, R=R)


class KeyboardPlacement(PlacementSource):
    """Placement based on a word or name (keyboard geometry)."""

    def __init__(self, word: str, K: int = 5, D: int = 8, lang: str = "en"):
        self.word = word
        self._K = K
        self._D = D
        self.lang = lang

    def identity_inputs(self) -> dict:
        return {"word": self.word, "language": self.lang}

    def parameters(self) -> dict:
        L = calculate_lsum(self.word, self.lang)
        S = calculate_ssum(self.word, self.lang)
        c = first_letter_index(self.word, self.lang)
        return {"L": L, "S": S, "c": c, "K": self._K, "D": self._D}


class GSGPlacement(PlacementSource):
    """Placement based on GPS coordinates (Guru Spatial Grid)."""

    def __init__(self, lat: float, lon: float, K: int = 5, D: int = 8):
        self.lat = lat
        self.lon = lon
        self._K = K
        self._D = D

    def identity_inputs(self) -> dict:
        return {"latitude": self.lat, "longitude": self.lon}

    def parameters(self) -> dict:
        (gsg_x, gsg_y), (L, S, c) = gps_to_gsg(self.lat, self.lon)
        return {"L": L, "S": S, "c": c, "K": self._K, "D": self._D,
                "gsg_cell": (gsg_x, gsg_y)}


class CrawlerPlacement(PlacementSource):
    """Placement for a crawled web page."""

    def __init__(self, url: str):
        self.url = url
        self._K = 27
        self._D = 27

    def identity_inputs(self) -> dict:
        return {"url": self.url}

    def parameters(self) -> dict:
        from urllib.parse import urlparse
        domain = urlparse(self.url).netloc
        first_letter = domain[0].lower() if domain else 'a'
        c = ord(first_letter) - 97 if 'a' <= first_letter <= 'z' else 0
        L = len(self.url)
        S = int(hashlib.sha256(self.url.encode()).hexdigest()[:8], 16) % 1_000_000
        return {"L": L, "S": S, "c": c, "K": self._K, "D": self._D}