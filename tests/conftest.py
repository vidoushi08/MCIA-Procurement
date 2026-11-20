import os
import tempfile

_db_file = os.path.join(tempfile.gettempdir(), "mcia_test.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_db_file}"
os.environ["APP_SECRET_KEY"] = "test-secret-key"

import pytest
from fastapi.testclient import TestClient

from src.app.database import Base, SessionLocal, engine
from src.app.main import app
from src.app.users.models import User
from src.app.inventory.models import InventoryItem
from src.app.security import hash_password

PASSWORD = "password123"


@pytest.fixture
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c


@pytest.fixture
def seeded(client):
    db = SessionLocal()
    try:
        users = {
            "staff@test.com": ("STAFF", "Finance"),
            "other@test.com": ("STAFF", "Operations"),
            "head@test.com": ("DEPT_HEAD", "Finance"),
            "admin@test.com": ("ADMIN", "Administration"),
        }
        for email, (role, dept) in users.items():
            db.add(User(
                full_name=email.split("@")[0],
                email=email,
                role=role,
                department=dept,
                password_hash=hash_password(PASSWORD),
            ))
        db.add(InventoryItem(item_name="A4 Paper", quantity_in_stock=50, department_category="Finance"))
        db.add(InventoryItem(item_name="Stapler", quantity_in_stock=0, department_category="Finance"))
        db.commit()
    finally:
        db.close()
    return client


def login(client, email):
    resp = client.post("/auth/login", json={"email": email, "password": PASSWORD})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['token']}"}
