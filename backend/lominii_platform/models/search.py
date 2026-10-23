from sqlalchemy import (
    Column,
    Integer,
    SmallInteger,
    String,
    Float,
    DateTime,
    ForeignKey,
    Text,
    UniqueConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from lominii_platform.database import Base
from lominii_platform.nsid import NSID


# ===========================================================================
# SEARCH
# ===========================================================================

class Search(Base):
    __tablename__ = "searches"
    __table_args__ = {"schema": "search"}

    id = Column(Integer, primary_key=True, autoincrement=True)

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.users.id", ondelete="CASCADE"),
    )

    query = Column(Text, nullable=False)
    gsp_cell = Column(String(10))

    nsid = Column(SmallInteger, default=NSID.SEARCH)
    created_at = Column(DateTime, server_default="now()")


class Trending(Base):
    __tablename__ = "trending"
    __table_args__ = {"schema": "search"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    query = Column(Text, nullable=False)
    count = Column(Integer, default=1)

    nsid = Column(SmallInteger, default=NSID.SEARCH)
    updated_at = Column(DateTime, server_default="now()")


class Correction(Base):
    __tablename__ = "corrections"
    __table_args__ = {"schema": "search"}

    id = Column(Integer, primary_key=True, autoincrement=True)

    misspelled = Column(Text, nullable=False)
    corrected = Column(Text, nullable=False)

    gsp_cell = Column(String(10))
    confidence = Column(Float, default=0.0)

    nsid = Column(SmallInteger, default=NSID.SEARCH)


class NewsArticle(Base):
    __tablename__ = "news_articles"
    __table_args__ = {"schema": "search"}

    id = Column(Integer, primary_key=True, autoincrement=True)

    category = Column(String(50), nullable=False)
    title = Column(Text, nullable=False)
    url = Column(Text, nullable=False)
    source = Column(String(255))
    published_at = Column(DateTime)

    inserted_at = Column(DateTime, server_default="now()")
    nsid = Column(SmallInteger, default=NSID.SEARCH)


class NewsCache(Base):
    __tablename__ = "news_cache"
    __table_args__ = {"schema": "search"}

    id = Column(Integer, primary_key=True, autoincrement=True)

    category = Column(String(50), unique=True, nullable=False)
    articles = Column(JSONB, nullable=False)

    nsid = Column(SmallInteger, default=NSID.SEARCH)
    cached_at = Column(DateTime, server_default="now()")


class DictionaryCache(Base):
    __tablename__ = "dictionary_cache"
    __table_args__ = {"schema": "search"}

    id = Column(Integer, primary_key=True, autoincrement=True)

    word = Column(String(255), unique=True, nullable=False)
    definition = Column(Text, nullable=False)
    language = Column(String(10), default="en")

    nsid = Column(SmallInteger, default=NSID.SEARCH)
    cached_at = Column(DateTime, server_default="now()")


class DictionaryGridEntry(Base):
    """External dictionary records indexed for keyboard/GSP-based retrieval."""
    __tablename__ = "dictionary_grid_entries"
    __table_args__ = (
        UniqueConstraint(
            "language", "normalized_word",
            name="uq_dictionary_grid_language_word",
        ),
        Index(
            "ix_dictionary_grid_primary_cell",
            "language", "primary_cell_col", "primary_cell_row",
        ),
        {"schema": "search"},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    word = Column(String(255), nullable=False)
    normalized_word = Column(String(255), nullable=False)
    language = Column(String(10), nullable=False, default="en")

    definition = Column(Text, nullable=False)
    phonetic = Column(String(255))
    part_of_speech = Column(String(100))
    source = Column(String(255), nullable=False, default="Dictionary API")
    source_url = Column(Text)

    # The same GSP calculation is used when indexing and querying.
    uid_chain = Column(JSONB, nullable=False, default=list)
    L_sum = Column(Integer, nullable=False)
    S_sum = Column(Integer, nullable=False)
    keyboard_column = Column(Integer, nullable=False)

    primary_cell_col = Column(Integer, nullable=False)
    primary_cell_row = Column(Integer, nullable=False)
    replica_cells = Column(JSONB, nullable=False, default=list)

    indexed_at = Column(DateTime, server_default="now()", nullable=False)
    last_seen_at = Column(DateTime, server_default="now()", nullable=False)


class SearchCache(Base):
    __tablename__ = "search_cache"
    __table_args__ = {"schema": "search"}

    id = Column(Integer, primary_key=True, autoincrement=True)

    cache_key = Column(String(64), unique=True, nullable=False)
    result = Column(JSONB, nullable=False)

    nsid = Column(SmallInteger, default=NSID.SEARCH)
    cached_at = Column(DateTime, server_default="now()")


class VideoCache(Base):
    __tablename__ = "video_cache"
    __table_args__ = {"schema": "search"}

    id = Column(Integer, primary_key=True, autoincrement=True)

    query = Column(Text, nullable=False)
    videos = Column(JSONB, nullable=False)

    nsid = Column(SmallInteger, default=NSID.SEARCH)
    cached_at = Column(DateTime, server_default="now()")