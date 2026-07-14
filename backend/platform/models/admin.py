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
# ADMIN
# ===========================================================================

class Occupancy(Base):
    __tablename__ = "occupancy"
    __table_args__ = {"schema": "admin"}

    col = Column(Integer, primary_key=True)
    row = Column(Integer, primary_key=True)

    searches = Column(Integer, default=0)
    games = Column(Integer, default=0)
    users = Column(Integer, default=0)
    messages = Column(Integer, default=0)

    api_calls = Column(Integer, default=0)
    cache_hits = Column(Integer, default=0)

    nsid = Column(SmallInteger, default=NSID.ADMIN)


class UsernameCell(Base):
    __tablename__ = "username_cells"
    __table_args__ = {"schema": "admin"}

    col = Column(Integer, primary_key=True)
    row = Column(Integer, primary_key=True)

    username = Column(String(255), nullable=False)

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.users.id"),
    )

    nsid = Column(SmallInteger, default=NSID.ADMIN)

    user = relationship("User")