from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from uuid import UUID

from platform.database import get_db
from platform.auth import get_current_user
from platform.gsp import calculate_lsum, calculate_ssum, first_letter_index, gsp_place
from platform.nsid import NSID
from platform.models import Message, User
from platform.schemas import MessageCreate, MessageOut


router = APIRouter(
    prefix="/api/social/messages",
    tags=["Social Messages"]
)

def get_conversation_cell(user1_name: str, user2_name: str) -> str:
    names = sorted([user1_name.strip().lower(), user2_name.strip().lower()])
    L = calculate_lsum(names[0]) + calculate_lsum(names[1])
    S = calculate_ssum(names[0]) + calculate_ssum(names[1])
    c = first_letter_index(names[0])
    cells = gsp_place(L, S, c, K=3, D=16)
    return cells[0]

@router.post("/", response_model=MessageOut)
def send_message(
    payload: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    recipient = db.query(User).filter_by(id=payload.recipient_id).first()
    if not recipient:
        raise HTTPException(status_code=404, detail="Recipient not found")

    L_sender = calculate_lsum(current_user.full_name)
    S_sender = calculate_ssum(current_user.full_name)
    c_sender = first_letter_index(current_user.full_name)
    sender_cell = gsp_place(L_sender, S_sender, c_sender, K=3, D=16)[0]
    conversation_cell = get_conversation_cell(current_user.full_name, recipient.full_name)

    msg = Message(
        sender_id=current_user.id,
        recipient_id=recipient.id,
        sender_cell=sender_cell,
        conversation_cell=conversation_cell,
        body=payload.body,
        media_url=payload.media_url,
        reply_to_id=payload.reply_to_id,
        nsid=NSID.SOCIAL
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg

@router.get("/conversations")
def list_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from sqlalchemy import func
    cells = db.query(Message.conversation_cell).filter(
        (Message.sender_id == current_user.id) | (Message.recipient_id == current_user.id),
        Message.deleted_at == None
    ).distinct().all()

    result = []
    for (cell,) in cells:
        last_msg = db.query(Message).filter(
            Message.conversation_cell == cell,
            Message.deleted_at == None
        ).order_by(Message.created_at.desc()).first()

        if last_msg:
            other_id = last_msg.sender_id if last_msg.sender_id != current_user.id else last_msg.recipient_id
            other_user = db.query(User).filter_by(id=other_id).first()
            result.append({
                "conversation_cell": cell,
                "other_user": other_user.full_name if other_user else "Unknown",
                "other_user_id": str(other_id),
                "last_message": last_msg.body,
                "last_time": last_msg.created_at.isoformat()
            })
    return result

@router.get("/with/{other_user_id}", response_model=List[MessageOut])
def get_messages(
    other_user_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    other_user = db.query(User).filter_by(id=other_user_id).first()
    if not other_user:
        raise HTTPException(status_code=404, detail="User not found")
    conv_cell = get_conversation_cell(current_user.full_name, other_user.full_name)

    messages = db.query(Message).filter(
        Message.conversation_cell == conv_cell,
        Message.deleted_at == None
    ).order_by(Message.created_at.desc()).offset(skip).limit(limit).all()

    return list(reversed(messages))