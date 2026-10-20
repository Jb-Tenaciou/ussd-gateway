import os
os.environ["DATABASE_URL"] = "sqlite:///./test.db"

import pytest
from fastapi.testclient import TestClient

from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import Role, User
from app.security import hash_password


@pytest.fixture()
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        db.add(User(full_name="Admin", phone_number="+25779000000", role=Role.ADMIN.value,
                    password_hash=hash_password("Admin12345")))
        db.add(User(full_name="Demo", phone_number="+25779111111", role=Role.DEMO_USER.value,
                    password_hash=hash_password("Demo12345")))
        db.commit()
    return TestClient(app)


def token(client, phone, pwd):
    r = client.post("/api/v1/auth/login", json={"phone_number": phone, "password": pwd})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture()
def admin(client):
    return token(client, "+25779000000", "Admin12345")


@pytest.fixture()
def demo(client):
    return token(client, "+25779111111", "Demo12345")
