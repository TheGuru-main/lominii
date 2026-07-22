"""
Related Algorithm Engine (Platform Layer)

Responsible for generating deterministic related-search candidates
before the Related Search Engine performs retrieval.

Pipeline

Query
    │
Three Circle
    │
Combinations
    │
Permutations
    │
Token Expansion
    │
Spelling Expansion
    │
Language Expansion
    │
Synonym Expansion
    │
BubbleJumbo Expansion
    │
Semantic Expansion
    │
Expansion Set
"""

from itertools import combinations, permutations
import re

class RelatedAlgorithm:
    """
    Core query expansion engine.

    This class is responsible only for generating
    candidate queries.

    It does NOT access the database, AI, crawler,
    cache or ranking system.
    """

    def _deduplicate(self, values: list[str]) -> list[str]:
    """
    Remove duplicates while preserving order.
    """
        return list(dict.fromkeys(values))

    async def three_circle(
        self,
        query: str,
        *,
        limit: int = 50,
    ) -> list[str]:
        """
        Generate first-ring semantic candidates.
        """

        query = " ".join(query.lower().split())

        words = query.split()

        circles = []

        # Original query
        circles.append(query)

        # Remove first word
        if len(words) > 1:
            circles.append(" ".join(words[1:]))

        # Remove last word
        if len(words) > 1:
            circles.append(" ".join(words[:-1]))

        # Individual words
        circles.extend(words)

        return self._deduplicate(circles)[:limit]

    async def combinations(
        self,
        query: str,
        *,
        max_length: int = 3,
    ) -> list[str]:
        """
        Generate deterministic word combinations.
        """

        words = query.lower().split()

        results = []

        limit = min(max_length, len(words))

        for size in range(2, limit + 1):
            for combo in combinations(words, size):
                results.append(" ".join(combo))

        return self._deduplicate(results)

    async def permutations(
        self,
        query: str,
        *,
        max_words: int = 4,
    ) -> list[str]:
        """
        Generate deterministic word permutations.
        """

        words = query.lower().split()

        if len(words) > max_words:
            words = words[:max_words]

        results = []

        for perm in permutations(words):
            results.append(" ".join(perm))

        return self._deduplicate(results)

    async def token_expansion(
        self,
        query: str,
    ) -> list[str]:
        """
        Expand a query into deterministic token sequences.

        Example:
            "How to learn python programming"

        Returns:
            [
                "how",
                "to",
                "learn",
                "python",
                "programming",
                "how to",
                "to learn",
                "learn python",
                "python programming",
                "how to learn",
                "to learn python",
                "learn python programming",
            ]
        """

        query = query.lower().strip()

   # Split on whitespace and punctuation
        tokens = [
            token
            for token in re.split(r"[^\w]+", query)
            if token
        ]

        results = []

        # Individual tokens
        results.extend(tokens)

        # Sliding windows
        n = len(tokens)

        for size in range(2, min(4, n) + 1):
            for i in range(n - size + 1):
                results.append(" ".join(tokens[i:i + size]))

        # Remove duplicates while preserving order
        return self._deduplicate(results)


    async def spelling_expansion(
        self,
        query: str,
    ) -> list[str]:
        """
        Generate spelling variants.

        (Implementation next.)
        """
        return []

    async def language_expansion(
        self,
        query: str,
    ) -> list[str]:
        """
        Generate multilingual variants.

        (Implementation next.)
        """
        return []

    async def synonym_expansion(
        self,
        query: str,
    ) -> list[str]:
        """
        Generate synonym candidates.

        (Implementation next.)
        """
        return []

    async def bubblejumbo_expansion(
        self,
        query: str,
    ) -> list[str]:
        """
        BubbleJumbo-based expansion.

        (Implementation after BubbleJumbo platform upgrade.)
        """
        return []

    async def semantic_expansion(
        self,
        query: str,
    ) -> list[str]:
        """
        Semantic concept expansion.

        (Implementation next.)
        """
        return []

    async def expand(
        self,
        query: str,
    ) -> list[str]:
        """
        Master expansion pipeline.
        """

        candidates = []

        candidates.extend(await self.three_circle(query))

        candidates.extend(await self.combinations(query))

        candidates.extend(await self.permutations(query))

        candidates.extend(await self.token_expansion(query))

        candidates.extend(await self.spelling_expansion(query))

        candidates.extend(await self.language_expansion(query))

        candidates.extend(await self.synonym_expansion(query))

        candidates.extend(await self.bubblejumbo_expansion(query))

        candidates.extend(await self.semantic_expansion(query))

        # Remove duplicates while preserving order
        return list(dict.fromkeys(candidates))