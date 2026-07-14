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

from sqlalchemy.dialects.postgresql import UUID, JSONB

from sqlalchemy.orm import relationship

from platform.database import Base
from platform.nsid import NSID

# ===========================================================================
# GAMES
# ===========================================================================

class GameSession(Base):
    __tablename__ = "game_sessions"
    __table_args__ = {"schema": "game"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    game_id = Column(String(20), nullable=False)
    room_id = Column(String(20), unique=True, nullable=False)

    players = Column(JSONB, nullable=False)
    game_state = Column(JSONB)

    status = Column(String(20), default="waiting")

    nsid = Column(SmallInteger, default=NSID.GAMES)

    created_at = Column(DateTime, server_default="now()")
    finished_at = Column(DateTime)


class Leaderboard(Base):
    __tablename__ = "leaderboards"
    __table_args__ = {"schema": "game"}

    id = Column(Integer, primary_key=True, autoincrement=True)

    game_id = Column(String(20), nullable=False)

    user_email = Column(String(255), nullable=False)

    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    draws = Column(Integer, default=0)

    points = Column(Integer, default=1000)

    nsid = Column(SmallInteger, default=NSID.GAMES)

    updated_at = Column(DateTime, server_default="now()")


class GameAchievement(Base):
    __tablename__ = "achievements"
    __table_args__ = {"schema": "game"}

    id = Column(Integer, primary_key=True, autoincrement=True)

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.users.id", ondelete="CASCADE"),
        nullable=False,
    )

    game_id = Column(String(20), nullable=False)

    achievement = Column(String(255), nullable=False)
    description = Column(Text)

    points = Column(Integer, default=0)

    nsid = Column(SmallInteger, default=NSID.GAMES)

    unlocked_at = Column(DateTime, server_default="now()")

    user = relationship("User")