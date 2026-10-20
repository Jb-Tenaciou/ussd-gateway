import secrets
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import audit, staff
from app.models import Transaction, TxStatus, User, utcnow
from app.schemas import TransactionCreate, TransactionOut, TransactionStatusUpdate

router = APIRouter(prefix="/api/v1/transactions", tags=["Transactions (simulées)"])

ALLOWED = {
    TxStatus.PENDING.value: {TxStatus.SUCCESS.value, TxStatus.FAILED.value, TxStatus.CANCELLED.value},
}


@router.post("", response_model=TransactionOut)
def create_transaction(data: TransactionCreate, db: Session = Depends(get_db), actor: User = Depends(staff)):
    """Idempotent : même idempotency_key => renvoie la transaction existante."""
    existing = db.scalar(select(Transaction).where(Transaction.idempotency_key == data.idempotency_key))
    if existing:
        return existing
    ref = f"DEMO-{datetime.now().strftime('%y%m%d')}-{secrets.token_hex(3).upper()}"
    tx = Transaction(reference=ref, user_id=data.user_id, session_id=data.session_id, amount=data.amount,
                     currency=data.currency, transaction_type=data.transaction_type.value,
                     idempotency_key=data.idempotency_key)
    db.add(tx)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return db.scalar(select(Transaction).where(Transaction.idempotency_key == data.idempotency_key))
    db.refresh(tx)
    audit(db, actor, "TX_CREATED", "transaction", tx.id)
    return tx


@router.get("", response_model=list[TransactionOut])
def list_transactions(status_: TxStatus | None = None, user_id: int | None = None, skip: int = 0, limit: int = 50,
                      db: Session = Depends(get_db), _: User = Depends(staff)):
    q = select(Transaction).order_by(Transaction.id.desc())
    if status_:
        q = q.where(Transaction.status == status_.value)
    if user_id:
        q = q.where(Transaction.user_id == user_id)
    return db.scalars(q.offset(skip).limit(min(limit, 200))).all()


@router.get("/by-reference/{reference}", response_model=TransactionOut)
def by_reference(reference: str, db: Session = Depends(get_db), _: User = Depends(staff)):
    tx = db.scalar(select(Transaction).where(Transaction.reference == reference))
    if not tx:
        raise HTTPException(404, "Transaction introuvable")
    return tx


@router.get("/{tx_id}", response_model=TransactionOut)
def get_transaction(tx_id: int, db: Session = Depends(get_db), _: User = Depends(staff)):
    tx = db.get(Transaction, tx_id)
    if not tx:
        raise HTTPException(404, "Transaction introuvable")
    return tx


@router.patch("/{tx_id}/status", response_model=TransactionOut)
def update_status(tx_id: int, data: TransactionStatusUpdate, db: Session = Depends(get_db), actor: User = Depends(staff)):
    tx = db.get(Transaction, tx_id)
    if not tx:
        raise HTTPException(404, "Transaction introuvable")
    if data.status.value not in ALLOWED.get(tx.status, set()):
        audit(db, actor, "TX_STATUS_REFUSED", "transaction", tx.id, "FAILED")
        raise HTTPException(status.HTTP_409_CONFLICT, f"Transition {tx.status} -> {data.status.value} interdite")
    tx.status = data.status.value
    tx.completed_at = utcnow()
    db.commit()
    db.refresh(tx)
    audit(db, actor, f"TX_{tx.status}", "transaction", tx.id)
    return tx
