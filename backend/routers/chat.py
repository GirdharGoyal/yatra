import time
from collections import defaultdict
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from backend.assistant.graph import run_yatra_assistant
from backend.auth import get_current_user
from backend.db import get_db
from backend.models import User
from backend.schemas import ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["Assistant"])

USER_TIMESTAMPS: Dict[int, List[float]] = defaultdict(list)
RATE_LIMIT_PER_MINUTE = 15


def _enforce_rate_limit(user_id: int) -> None:
    now = time.time()
    recent = [t for t in USER_TIMESTAMPS[user_id] if now - t < 60.0]
    if len(recent) >= RATE_LIMIT_PER_MINUTE:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded (max 15 messages/minute). Please wait a moment.",
        )
    recent.append(now)
    USER_TIMESTAMPS[user_id] = recent


@router.post("", response_model=ChatResponse)
async def chat_with_assistant(
    payload: ChatRequest,
    authorization: Optional[str] = Header(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _enforce_rate_limit(current_user.id)

    token = ""
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()

    result = await run_yatra_assistant(
        db=db,
        user=current_user,
        token=token,
        message=payload.message,
        resume=payload.resume,
    )
    return ChatResponse(**result)