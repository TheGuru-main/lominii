"""Pydantic schemas for request/response validation"""
from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime


# ---------- Messaging ----------
class MessageCreate(BaseModel):
    recipient_id: UUID
    body: str
    media_url: Optional[str] = None
    reply_to_id: Optional[UUID] = None


class MessageOut(BaseModel):
    id: UUID
    sender_id: UUID
    recipient_id: UUID
    sender_cell: str
    conversation_cell: str
    body: Optional[str]
    media_url: Optional[str]
    reply_to_id: Optional[UUID]
    is_edited: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        orm_mode = True