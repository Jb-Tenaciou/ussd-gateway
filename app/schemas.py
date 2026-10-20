import re
from datetime import datetime
from decimal import Decimal
from typing import Optional

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


class UserCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    phone_number: str
    password: Optional[str] = Field(default=None, min_length=8, max_length=128)
    role: Role = Role.DEMO_USER

    _p = field_validator("phone_number")(_check_phone)


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    role: Optional[Role] = None
    is_active: Optional[bool] = None


class UserOut(ORM):
    id: int
    full_name: str
    phone_number: str
    role: Role
    is_active: bool
    created_at: datetime


class SessionCreate(BaseModel):
    session_code: Optional[str] = Field(default=None, max_length=64)
    phone_number: str
    user_id: Optional[int] = None
    current_menu: str = "MAIN"

    _p = field_validator("phone_number")(_check_phone)


class SessionUpdate(BaseModel):
    current_menu: Optional[str] = Field(default=None, max_length=50)
    session_state: Optional[SessionState] = None


class SessionOut(ORM):
    id: int
    session_code: str
    user_id: Optional[int]
    phone_number: str
    current_menu: str
    session_state: SessionState
    started_at: datetime
    last_activity_at: datetime
    ended_at: Optional[datetime]


class InteractionCreate(BaseModel):
    menu_code: str = Field(max_length=50)
    user_input: Optional[str] = Field(default=None, max_length=255)
    system_response: Optional[str] = Field(default=None, max_length=2000)


class InteractionOut(ORM):
    id: int
    session_id: int
    menu_code: str
    user_input: Optional[str]
    system_response: Optional[str]
    step_number: int
    created_at: datetime


class TransactionCreate(BaseModel):
    user_id: Optional[int] = None
    session_id: Optional[int] = None
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
    user_id: Optional[int]
    session_id: Optional[int]
    amount: Decimal
    currency: str
    transaction_type: TxType
    status: TxStatus
    idempotency_key: str
    created_at: datetime
    completed_at: Optional[datetime]


class SmsCreate(BaseModel):
    phone_number: str
    direction: SmsDirection = SmsDirection.OUTBOUND
    message_text: str = Field(min_length=1, max_length=640)
    transaction_id: Optional[int] = None
    provider_reference: Optional[str] = Field(default=None, max_length=100)

    _p = field_validator("phone_number")(_check_phone)


class SmsStatusUpdate(BaseModel):
    status: SmsStatus


class SmsOut(ORM):
    id: int
    transaction_id: Optional[int]
    phone_number: str
    direction: SmsDirection
    message_text: str
    status: SmsStatus
    provider_reference: Optional[str]
    created_at: datetime
    sent_at: Optional[datetime]


class AuditCreate(BaseModel):
    action: str = Field(max_length=100)
    resource_type: str = Field(max_length=50)
    resource_id: Optional[str] = Field(default=None, max_length=64)
    result: str = Field(max_length=20)


class AuditOut(ORM):
    id: int
    actor_user_id: Optional[int]
    action: str
    resource_type: str
    resource_id: Optional[str]
    result: str
    created_at: datetime
