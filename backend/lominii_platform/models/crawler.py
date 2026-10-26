from sqlalchemy import (
    Column,
    SmallInteger,
    String,
    Float,
    DateTime,
    Text,
)

from sqlalchemy.dialects.postgresql import JSONB

from lominii_platform.database import Base
from lominii_platform.nsid import NSID


# ===========================================================================
# CRAWLER
# ===========================================================================

class CrawlerPage(Base):
    __tablename__ = "pages"
    __table_args__ = {"schema": "crawler"}

    url_hash = Column(String(64), primary_key=True)

    url = Column(Text, nullable=False)
    gsp_cell = Column(String(10))

    title = Column(Text)
    content = Column(Text)

    out_links = Column(JSONB, default=[])

    pagerank = Column(Float, default=0.0)

    nsid = Column(SmallInteger, default=NSID.CRAWLER)

    last_crawled = Column(DateTime, server_default="now()")

# ===========================================================================
# WEBSITE LEXICAL INDEX
# Indexes words and character positions extracted from resolved web pages.
# ===========================================================================

from sqlalchemy import Integer, ForeignKey, Index


class CrawlerWebsiteToken(Base):
    __tablename__ = "website_tokens"
    __table_args__ = (
        Index("ix_crawler_website_tokens_token", "normalized_token"),
        Index("ix_crawler_website_tokens_page", "url_hash"),
        Index(
            "ix_crawler_website_tokens_token_language",
            "normalized_token",
            "language",
        ),
        {"schema": "crawler"},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)

    url_hash = Column(
        String(64),
        ForeignKey("crawler.pages.url_hash", ondelete="CASCADE"),
        nullable=False,
    )

    normalized_token = Column(String(255), nullable=False)
    original_token = Column(Text, nullable=False)
    language = Column(String(16), nullable=False, default="en")

    # title, heading, or body
    section = Column(String(20), nullable=False, default="body")

    # Position of the token within its section.
    token_position = Column(Integer, nullable=False, default=0)

    # Character offset within the section text.
    char_start = Column(Integer, nullable=False, default=0)


class CrawlerWebsiteCharacter(Base):
    __tablename__ = "website_characters"
    __table_args__ = (
        Index(
            "ix_crawler_website_characters_char",
            "character",
        ),
        Index(
            "ix_crawler_website_characters_page",
            "url_hash",
        ),
        {"schema": "crawler"},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)

    url_hash = Column(
        String(64),
        ForeignKey("crawler.pages.url_hash", ondelete="CASCADE"),
        nullable=False,
    )

    # One character from a normalized token.
    character = Column(String(1), nullable=False)

    # Position within the normalized token.
    character_position = Column(Integer, nullable=False)

    normalized_token = Column(String(255), nullable=False)
    language = Column(String(16), nullable=False, default="en")
    section = Column(String(20), nullable=False, default="body")
    token_position = Column(Integer, nullable=False, default=0)
