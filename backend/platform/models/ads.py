import uuid

from sqlalchemy import (
    Column,
    Integer,
    SmallInteger,
    String,
    Float,
    DateTime,
    ForeignKey,
    Boolean,
    JSON,
    Text,
)

from sqlalchemy.dialects.postgresql import (
    UUID,
    JSONB,
)

from sqlalchemy.orm import relationship

from platform.database import Base
from platform.nsid import NSID


# ===========================================================================
# ADS
# ===========================================================================

class SponsoredCell(Base):
    __tablename__ = "sponsored_cells"
    __table_args__ = {"schema": "ads"}

    id = Column(Integer, primary_key=True, autoincrement=True)

    advertiser_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.users.id", ondelete="CASCADE"),
        nullable=False,
    )

    col = Column(Integer, nullable=False)
    row = Column(Integer, nullable=False)

    ad_content = Column(JSONB)

    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)

    active = Column(Boolean, default=True)

    nsid = Column(SmallInteger, default=NSID.SHOP)

    advertiser = relationship("User")