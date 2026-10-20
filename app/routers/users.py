from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import admin_only, audit, staff
from app.models import User
from app.schemas import UserCreate, UserOut, UserUpdate
from app.security import hash_password

router = APIRouter(prefix="/api/v1/users", tags=["Users"])


@router.post("", response_model=UserOut, status_code=201)
def create_user(data: UserCreate, db: Session = Depends(get_db), actor: User = Depends(admin_only)):
    if db.scalar(select(User).where(User.phone_number == data.phone_number)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Numéro déjà enregistré")
    user = User(full_name=data.full_name, phone_number=data.phone_number, role=data.role.value,
                password_hash=hash_password(data.password) if data.password else None)
    db.add(user)
    db.commit()
    db.refresh(user)
    audit(db, actor, "USER_CREATED", "user", user.id)
    return user


@router.get("", response_model=list[UserOut])
def list_users(skip: int = 0, limit: int = 50, db: Session = Depends(get_db), _: User = Depends(staff)):
    return db.scalars(select(User).order_by(User.id).offset(skip).limit(min(limit, 200))).all()


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: int, db: Session = Depends(get_db), _: User = Depends(staff)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "Utilisateur introuvable")
    return user


@router.patch("/{user_id}", response_model=UserOut)
def update_user(user_id: int, data: UserUpdate, db: Session = Depends(get_db), actor: User = Depends(admin_only)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "Utilisateur introuvable")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(user, k, v.value if hasattr(v, "value") else v)
    db.commit()
    db.refresh(user)
    audit(db, actor, "USER_UPDATED", "user", user.id)
    return user
