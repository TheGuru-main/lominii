from sqlalchemy import (
    Column,
    Integer,
    SmallInteger,
    String,
    Float,
    DateTime,
    ForeignKey,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from platform.database import Base
from platform.nsid import NSID


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