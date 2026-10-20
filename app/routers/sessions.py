import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import audit, staff
from app.models import SessionState, User, UssdInteraction, UssdSession, utcnow
from app.schemas import (
    InteractionCreate,
    InteractionOut,
    SessionCreate,
    SessionOut,
    SessionUpdate,
)

router = APIRouter(prefix="/api/v1/sessions", tags=["USSD sessions"])


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def _get(db: Session, session_id: int) -> UssdSession:
    s = db.get(UssdSession, session_id)
    if not s:
        raise HTTPException(404, "Session introuvable")
    return s


def _expire_if_needed(db: Session, s: UssdSession) -> None:
    if s.session_state == SessionState.ACTIVE.value:
        idle = (utcnow() - _aware(s.last_activity_at)).total_seconds()
        if idle > settings.SESSION_TIMEOUT_SECONDS:
            s.session_state = SessionState.EXPIRED.value
            s.ended_at = utcnow()
            db.commit()


@router.post("", response_model=SessionOut, status_code=201)
def create_session(data: SessionCreate, db: Session = Depends(get_db), actor: User = Depends(staff)):
    code = data.session_code or uuid.uuid4().hex
    if db.scalar(select(UssdSession).where(UssdSession.session_code == code)):
        raise HTTPException(status.HTTP_409_CONFLICT, "session_code déjà utilisé")
    s = UssdSession(session_code=code, phone_number=data.phone_number, user_id=data.user_id,
                    current_menu=data.current_menu)
    db.add(s)
    db.commit()
    db.refresh(s)
    audit(db, actor, "SESSION_STARTED", "ussd_session", s.id)
    return s


@router.get("", response_model=list[SessionOut])
def list_sessions(state: SessionState | None = None, phone_number: str | None = None,
                  skip: int = 0, limit: int = 50, db: Session = Depends(get_db), _: User = Depends(staff)):
    q = select(UssdSession).order_by(UssdSession.id.desc())
    if state:
        q = q.where(UssdSession.session_state == state.value)
    if phone_number:
        q = q.where(UssdSession.phone_number == phone_number)
    return db.scalars(q.offset(skip).limit(min(limit, 200))).all()


@router.get("/{session_id}", response_model=SessionOut)
def get_session(session_id: int, db: Session = Depends(get_db), _: User = Depends(staff)):
    s = _get(db, session_id)
    _expire_if_needed(db, s)
    return s


@router.patch("/{session_id}", response_model=SessionOut)
def update_session(session_id: int, data: SessionUpdate, db: Session = Depends(get_db), actor: User = Depends(staff)):
    s = _get(db, session_id)
    _expire_if_needed(db, s)
    if s.session_state != SessionState.ACTIVE.value:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Session déjà {s.session_state}")
    if data.current_menu:
        s.current_menu = data.current_menu
    s.last_activity_at = utcnow()
    if data.session_state and data.session_state != SessionState.ACTIVE:
        s.session_state = data.session_state.value
        s.ended_at = utcnow()
        audit(db, actor, f"SESSION_{data.session_state.value}", "ussd_session", s.id)
    db.commit()
    db.refresh(s)
    return s


@router.post("/{session_id}/interactions", response_model=InteractionOut, status_code=201)
def add_interaction(session_id: int, data: InteractionCreate, db: Session = Depends(get_db), _: User = Depends(staff)):
    s = _get(db, session_id)
    _expire_if_needed(db, s)
    if s.session_state != SessionState.ACTIVE.value:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Session déjà {s.session_state}")
    step = (db.scalar(select(func.max(UssdInteraction.step_number)).where(UssdInteraction.session_id == s.id)) or 0) + 1
    i = UssdInteraction(session_id=s.id, step_number=step, **data.model_dump())
    s.last_activity_at = utcnow()
    db.add(i)
    db.commit()
    db.refresh(i)
    return i


@router.get("/{session_id}/interactions", response_model=list[InteractionOut])
def list_interactions(session_id: int, db: Session = Depends(get_db), _: User = Depends(staff)):
    _get(db, session_id)
    return db.scalars(select(UssdInteraction).where(UssdInteraction.session_id == session_id)
                      .order_by(UssdInteraction.step_number)).all()
