class RelatedAlgorithm:

    async def three_circle(
        self,
        query: str,
        *,
        limit: int = 50,
    ):
        """
        Generate first-ring semantic candidates.
        """
        ...

    async def combinations(
        self,
        query: str,
        *,
        max_length: int = 3,
    ):
        """
        Generate deterministic word combinations.
        """
        ...

    async def permutations(
        self,
        query: str,
        *,
        max_words: int = 4,
    ):
        """
        Generate deterministic word permutations.
        """
        ...

    async def token_expansion(
        self,
        query: str,
    ):
        ...

    async def synonym_expansion(
        self,
        query: str,
    ):
        ...

    async def language_expansion(
        self,
        query: str,
    ):
        ...

    async def bubblejumbo_expansion(
        self,
        query: str,
    ):
        ...

    async def semantic_expansion(
        self,
        query: str,
    ):
        ...

    async def spelling_expansion(
        self,
        query: str,
    ):
        ...

    async def expand(
        self,
        query: str,
    ):
        """
        Master expansion pipeline.
        """
        ...