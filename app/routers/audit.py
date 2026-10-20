from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import admin_only, staff
from app.models import AuditLog, User
from app.schemas import AuditCreate, AuditOut

router = APIRouter(prefix="/api/v1/audit-logs", tags=["Audit"])


@router.post("", response_model=AuditOut, status_code=201)
def create(data: AuditCreate, db: Session = Depends(get_db), actor: User = Depends(staff)):
    log = AuditLog(actor_user_id=actor.id, **data.model_dump())
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


@router.get("", response_model=list[AuditOut])
def list_logs(action: str | None = None, skip: int = 0, limit: int = 100,
              db: Session = Depends(get_db), _: User = Depends(admin_only)):
    q = select(AuditLog).order_by(AuditLog.id.desc())
    if action:
        q = q.where(AuditLog.action == action)
    return db.scalars(q.offset(skip).limit(min(limit, 500))).all()
