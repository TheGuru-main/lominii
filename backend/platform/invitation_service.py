"""
LOMINII Invitation Service

One invitation system shared by:
- Search
- Social
- Play
- EDU
- Quran

Every workspace sends invitations through this service.
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, Optional

# Active invitations kept in memory.
# Later this can be moved to Redis or PostgreSQL.
active_invitations: Dict[str, dict] = {}


async def create_invitation(
    sender_id: str,
    receiver_id: str,
    workspace: str,
    destination: str,
    payload: Optional[dict] = None,
):
    invitation_id = uuid.uuid4().hex

    invitation = {
        "invitation_id": invitation_id,
        "sender_id": sender_id,
        "receiver_id": receiver_id,
        "workspace": workspace,
        "destination": destination,
        "payload": payload or {},
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat()
    }

    active_invitations[invitation_id] = invitation

    return invitation


async def get_invitation(invitation_id: str):
    return active_invitations.get(invitation_id)


async def accept_invitation(invitation_id: str):
    invitation = active_invitations.get(invitation_id)

    if not invitation:
        return None

    invitation["status"] = "accepted"

    return invitation


async def decline_invitation(invitation_id: str):
    invitation = active_invitations.get(invitation_id)

    if not invitation:
        return None

    invitation["status"] = "declined"

    return invitation


async def revoke_invitation(invitation_id: str):
    return active_invitations.pop(invitation_id, None)


async def user_pending_invitations(user_id: str):
    return [
        invitation
        for invitation in active_invitations.values()
        if invitation["receiver_id"] == user_id
        and invitation["status"] == "pending"
    ]