import enum
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class Role(str, enum.Enum):
    ADMIN = "ADMIN"
    OPERATOR = "OPERATOR"
    DEMO_USER = "DEMO_USER"


class SessionState(str, enum.Enum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class TxStatus(str, enum.Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class TxType(str, enum.Enum):
    PAYMENT = "PAYMENT"
    SAVINGS = "SAVINGS"


class SmsDirection(str, enum.Enum):
    INBOUND = "INBOUND"
    OUTBOUND = "OUTBOUND"


class SmsStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    SENT = "SENT"
    FAILED = "FAILED"
    RECEIVED = "RECEIVED"


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120))
    phone_number: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(20), default=Role.DEMO_USER.value)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    sessions: Mapped[list["UssdSession"]] = relationship(back_populates="user")


class UssdSession(Base):
    __tablename__ = "ussd_sessions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    phone_number: Mapped[str] = mapped_column(String(20), index=True)
    current_menu: Mapped[str] = mapped_column(String(50), default="MAIN")
    session_state: Mapped[str] = mapped_column(String(20), default=SessionState.ACTIVE.value, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_activity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User | None] = relationship(back_populates="sessions")
    interactions: Mapped[list["UssdInteraction"]] = relationship(back_populates="session", cascade="all, delete-orphan")


class UssdInteraction(Base):
    __tablename__ = "ussd_interactions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("ussd_sessions.id"), index=True)
    menu_code: Mapped[str] = mapped_column(String(50))
    user_input: Mapped[str | None] = mapped_column(String(255), nullable=True)
    system_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    step_number: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    session: Mapped[UssdSession] = relationship(back_populates="interactions")


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_transactions_idempotency_key"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    reference: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    session_id: Mapped[int | None] = mapped_column(ForeignKey("ussd_sessions.id"), nullable=True, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    currency: Mapped[str] = mapped_column(String(3), default="BIF")
    transaction_type: Mapped[str] = mapped_column(String(20), default=TxType.PAYMENT.value)
    status: Mapped[str] = mapped_column(String(20), default=TxStatus.PENDING.value, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SmsMessage(Base):
    __tablename__ = "sms_messages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    transaction_id: Mapped[int | None] = mapped_column(ForeignKey("transactions.id"), nullable=True, index=True)
    phone_number: Mapped[str] = mapped_column(String(20), index=True)
    direction: Mapped[str] = mapped_column(String(10))
    message_text: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(10), default=SmsStatus.QUEUED.value)
    provider_reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(100), index=True)
    resource_type: Mapped[str] = mapped_column(String(50))
    resource_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    result: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
