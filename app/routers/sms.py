from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import staff
from app.models import SmsMessage, SmsStatus, User, utcnow
from app.schemas import SmsCreate, SmsOut, SmsStatusUpdate

router = APIRouter(prefix="/api/v1/sms", tags=["SMS (simulés)"])


@router.post("", response_model=SmsOut, status_code=201)
def create_sms(data: SmsCreate, db: Session = Depends(get_db), _: User = Depends(staff)):
    status_ = SmsStatus.RECEIVED if data.direction.value == "INBOUND" else SmsStatus.QUEUED
    sms = SmsMessage(status=status_.value, direction=data.direction.value, phone_number=data.phone_number,
                     message_text=data.message_text, transaction_id=data.transaction_id,
                     provider_reference=data.provider_reference)
    db.add(sms)
    db.commit()
    db.refresh(sms)
    return sms


@router.get("", response_model=list[SmsOut])
def list_sms(phone_number: str | None = None, transaction_id: int | None = None, skip: int = 0, limit: int = 50,
             db: Session = Depends(get_db), _: User = Depends(staff)):
    q = select(SmsMessage).order_by(SmsMessage.id.desc())
    if phone_number:
        q = q.where(SmsMessage.phone_number == phone_number)
    if transaction_id:
        q = q.where(SmsMessage.transaction_id == transaction_id)
    return db.scalars(q.offset(skip).limit(min(limit, 200))).all()


@router.patch("/{sms_id}/status", response_model=SmsOut)
def update_sms_status(sms_id: int, data: SmsStatusUpdate, db: Session = Depends(get_db), _: User = Depends(staff)):
    sms = db.get(SmsMessage, sms_id)
    if not sms:
        raise HTTPException(404, "SMS introuvable")
    sms.status = data.status.value
    if data.status == SmsStatus.SENT:
        sms.sent_at = utcnow()
    db.commit()
    db.refresh(sms)
    return sms
