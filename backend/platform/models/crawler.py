from sqlalchemy import (
    Column,
    SmallInteger,
    String,
    Float,
    DateTime,
    Text,
)

from sqlalchemy.dialects.postgresql import JSONB

from platform.database import Base
from platform.nsid import NSID


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