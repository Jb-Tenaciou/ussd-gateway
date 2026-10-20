from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import audit, get_current_user
from app.models import User
from app.schemas import LoginRequest, Token, UserOut
from app.security import create_access_token, verify_password

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])


@router.post("/login", response_model=Token)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.phone_number == data.phone_number))
    if not user or not user.is_active or not verify_password(data.password, user.password_hash):
        audit(db, None, "LOGIN", "user", user.id if user else None, "FAILED")
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Identifiants invalides")
    audit(db, user, "LOGIN", "user", user.id)
    return Token(access_token=create_access_token(user.id, user.role))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
