import re
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import Role, SessionState, SmsDirection, SmsStatus, TxStatus, TxType

PHONE_RE = re.compile(r"^\+?[0-9]{8,15}$")


def _check_phone(v: str) -> str:
    v = v.strip().replace(" ", "")
    if not PHONE_RE.match(v):
        raise ValueError("Numéro invalide (8 à 15 chiffres, '+' optionnel)")
    return v


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    phone_number: str
    password: str

    _p = field_validator("phone_number")(_check_phone)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ChangePassword(BaseModel):
    old_password: str
    new_password: str = Field(min_length=8, max_length=128)


class UserCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    phone_number: str
    password: str | None = Field(default=None, min_length=8, max_length=128)
    role: Role = Role.DEMO_USER

    _p = field_validator("phone_number")(_check_phone)


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    role: Role | None = None
    is_active: bool | None = None


class UserOut(ORM):
    id: int
    full_name: str
    phone_number: str
    role: Role
    is_active: bool
    created_at: datetime


class SessionCreate(BaseModel):
    session_code: str | None = Field(default=None, max_length=64)
    phone_number: str
    user_id: int | None = None
    current_menu: str = "MAIN"

    _p = field_validator("phone_number")(_check_phone)


class SessionUpdate(BaseModel):
    current_menu: str | None = Field(default=None, max_length=50)
    session_state: SessionState | None = None


class SessionOut(ORM):
    id: int
    session_code: str
    user_id: int | None
    phone_number: str
    current_menu: str
    session_state: SessionState
    started_at: datetime
    last_activity_at: datetime
    ended_at: datetime | None


class InteractionCreate(BaseModel):
    menu_code: str = Field(max_length=50)
    user_input: str | None = Field(default=None, max_length=255)
    system_response: str | None = Field(default=None, max_length=2000)


class InteractionOut(ORM):
    id: int
    session_id: int
    menu_code: str
    user_input: str | None
    system_response: str | None
    step_number: int
    created_at: datetime


class TransactionCreate(BaseModel):
    user_id: int | None = None
    session_id: int | None = None
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    currency: str = Field(default="BIF", min_length=3, max_length=3)
    transaction_type: TxType = TxType.PAYMENT
    idempotency_key: str = Field(min_length=8, max_length=100)

    @field_validator("currency")
    @classmethod
    def upper(cls, v: str) -> str:
        return v.upper()


class TransactionStatusUpdate(BaseModel):
    status: TxStatus


class TransactionOut(ORM):
    id: int
    reference: str
    user_id: int | None
    session_id: int | None
    amount: Decimal
    currency: str
    transaction_type: TxType
    status: TxStatus
    idempotency_key: str
    created_at: datetime
    completed_at: datetime | None


class SmsCreate(BaseModel):
    phone_number: str
    direction: SmsDirection = SmsDirection.OUTBOUND
    message_text: str = Field(min_length=1, max_length=640)
    transaction_id: int | None = None
    provider_reference: str | None = Field(default=None, max_length=100)

    _p = field_validator("phone_number")(_check_phone)


class SmsStatusUpdate(BaseModel):
    status: SmsStatus


class SmsOut(ORM):
    id: int
    transaction_id: int | None
    phone_number: str
    direction: SmsDirection
    message_text: str
    status: SmsStatus
    provider_reference: str | None
    created_at: datetime
    sent_at: datetime | None


class AuditCreate(BaseModel):
    action: str = Field(max_length=100)
    resource_type: str = Field(max_length=50)
    resource_id: str | None = Field(default=None, max_length=64)
    result: str = Field(max_length=20)


class AuditOut(ORM):
    id: int
    actor_user_id: int | None
    action: str
    resource_type: str
    resource_id: str | None
    result: str
    created_at: datetime
