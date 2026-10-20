import time
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import audit, get_current_user
from app.models import User
from app.schemas import ChangePassword, LoginRequest, Token, UserOut
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])

# Anti brute-force simple (mémoire du processus) : numéro -> horodatages des échecs
_failures: dict[str, list[float]] = defaultdict(list)


def _check_lock(phone: str) -> None:
    window = settings.LOGIN_LOCK_MINUTES * 60
    now = time.time()
    _failures[phone] = [t for t in _failures[phone] if now - t < window]
    if len(_failures[phone]) >= settings.LOGIN_MAX_ATTEMPTS:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                            f"Trop de tentatives. Réessayez dans {settings.LOGIN_LOCK_MINUTES} minutes.")


@router.post("/login", response_model=Token)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    _check_lock(data.phone_number)
    user = db.scalar(select(User).where(User.phone_number == data.phone_number))
    if not user or not user.is_active or not verify_password(data.password, user.password_hash):
        _failures[data.phone_number].append(time.time())
        audit(db, None, "LOGIN", "user", user.id if user else None, "FAILED")
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Identifiants invalides")
    _failures.pop(data.phone_number, None)
    audit(db, user, "LOGIN", "user", user.id)
    return Token(access_token=create_access_token(user.id, user.role))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.post("/change-password", status_code=204)
def change_password(data: ChangePassword, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not verify_password(data.old_password, user.password_hash):
        audit(db, user, "PASSWORD_CHANGE", "user", user.id, "FAILED")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Ancien mot de passe incorrect")
    user.password_hash = hash_password(data.new_password)
    db.commit()
    audit(db, user, "PASSWORD_CHANGE", "user", user.id)
