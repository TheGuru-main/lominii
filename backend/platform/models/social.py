import uuid

from sqlalchemy import (
    Column,
    SmallInteger,
    String,
    DateTime,
    ForeignKey,
    Boolean,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from platform.database import Base
from platform.nsid import NSID

