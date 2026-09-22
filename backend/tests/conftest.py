import os
import tempfile

# Force a fresh isolated database before any app module is imported.
os.environ["DATABASE_URL"] = "sqlite:///./test_laptop_allocation.db"

if os.path.exists("test_laptop_allocation.db"):
    os.remove("test_laptop_allocation.db")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.database import engine, Base, SessionLocal
from app.main import app
from app.models.seed import seed_all, seed_demo_data


@pytest.fixture(scope="function", autouse=True)
def setup_database():
    # Recreate all tables fresh for each test to guarantee full isolation.
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_all(db)
        seed_demo_data(db)
    finally:
        db.close()
    yield


@pytest.fixture()
def client(setup_database):
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_admin_token(client: TestClient) -> str:
    resp = client.post(
        "/api/v1/auth/login",
        data={"username": "admin", "password": "admin123"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest.fixture()
def admin_headers(client):
    token = get_admin_token(client)
    return {"Authorization": f"Bearer {token}"}
