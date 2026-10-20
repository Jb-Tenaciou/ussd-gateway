"""Usage : python seed.py +25779000000 'MotDePasseSolide123' "Admin Labo" """
import sys

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Role, User
from app.security import hash_password

phone, pwd = sys.argv[1], sys.argv[2]
name = sys.argv[3] if len(sys.argv) > 3 else "Admin"
with SessionLocal() as db:
    if db.scalar(select(User).where(User.phone_number == phone)):
        print("Existe déjà")
    else:
        db.add(User(full_name=name, phone_number=phone, role=Role.ADMIN.value, password_hash=hash_password(pwd)))
        db.commit()
        print("Admin créé")
