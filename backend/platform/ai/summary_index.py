"""
AI Summary Index Service

Deterministic indexing of AI summaries using
SHA256 + GSP placement.

This service never stores the summary itself.
It only maintains the directory/index.
"""

import hashlib
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from platform.gsp import gsp_place

from platform.models.ai import AISummaryIndex


class AISummaryIndexService:

    def __init__(self, db: AsyncSession):
        self.db = db

    # --------------------------------------------------
    # Query Normalization
    # --------------------------------------------------

    def normalize_query(self, query: str) -> str:
        return " ".join(
            query.lower().strip().split()
        )

    # --------------------------------------------------
    # Cache Key
    # --------------------------------------------------

    def build_cache_key(
        self,
        query: str,
        domain: str,
        language: str = "en",
    ) -> str:

        normalized = self.normalize_query(query)

        payload = (
            f"{domain}|{language}|{normalized}"
        )

        return hashlib.sha256(
            payload.encode()
        ).hexdigest()[:16]

    # --------------------------------------------------
    # Query Hash
    # --------------------------------------------------

    def build_query_hash(
        self,
        query: str,
    ) -> str:

        return hashlib.sha256(
            self.normalize_query(query).encode()
        ).hexdigest()

    # --------------------------------------------------
    # Compute GSP Identity
    # --------------------------------------------------

    def compute_identity(
        self,
        cache_key: str,
    ):

        L = len(cache_key)

        S = int(
            cache_key,
            16
        ) % 1_000_000

        c = 0

        return L, S, c

    # --------------------------------------------------
    # Locate Cells
    # --------------------------------------------------

    def locate_cells(
        self,
        L,
        S,
        c,
    ):

        return gsp_place(
            L=L,
            S=S,
            c=c,
            K=5,
            D=8,
            C=26,
            R=64,
        )

    # --------------------------------------------------
    # Lookup
    # --------------------------------------------------

    async def lookup(
        self,
        cache_key: str,
    ):

        stmt = select(
            AISummaryIndex
        ).where(
            AISummaryIndex.cache_key == cache_key
        )

        result = await self.db.execute(stmt)

        return result.scalar_one_or_none()

    # --------------------------------------------------
    # Register
    # --------------------------------------------------

    async def register(
        self,
        query: str,
        domain: str,
        language="en",
        model_version=None,
    ):

        cache_key = self.build_cache_key(
            query,
            domain,
            language,
        )

        existing = await self.lookup(
            cache_key
        )

        if existing:
            return existing

        L, S, c = self.compute_identity(
            cache_key
        )

        placement = self.locate_cells(
            L,
            S,
            c,
        )

        primary = placement["primary_cell"]

        index = AISummaryIndex(

            cache_key=cache_key,

            query_hash=self.build_query_hash(
                query
            ),

            normalized_query=self.normalize_query(
                query
            ),

            domain=domain,

            language=language,

            L=L,
            S=S,
            c=c,

            primary_column=primary["col"],
            primary_row=primary["row"],

            model_version=model_version,

        )

        self.db.add(index)

        await self.db.commit()

        await self.db.refresh(index)

        return index

    # --------------------------------------------------
    # Touch
    # --------------------------------------------------

    async def touch(
        self,
        index: AISummaryIndex,
    ):

        index.access_count += 1

        index.last_accessed = datetime.utcnow()

        await self.db.commit()

    # --------------------------------------------------
    # Export Dataset
    # --------------------------------------------------

    async def export_dataset(self):

        stmt = select(
            AISummaryIndex
        )

        result = await self.db.execute(stmt)

        return result.scalars().all()