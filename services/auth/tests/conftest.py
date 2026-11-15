import os

os.environ.update(DATABASE_URL="sqlite://", JWT_SECRET="test-secret-test-secret-test-secret-0123456789", BCRYPT_ROUNDS="4")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from hotstar_common.db import Base  # noqa: E402

from app.db import engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def _schema():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def register(client, email="viewer@example.com", username="viewer", password="Passw0rd!x"):
    return client.post("/auth/register", json={"email": email, "username": username, "password": password})


@pytest.fixture
def user_tokens(client):
    return register(client).json()


@pytest.fixture
def admin_headers(client):
    from app.db import SessionLocal
    from app.models import User
    from app.passwords import hash_password

    with SessionLocal() as db:
        db.add(User(email="admin@example.com", username="admin", password_hash=hash_password("Adm1nPass!"), role="admin"))
        db.commit()
    tok = client.post("/auth/login", json={"email": "admin@example.com", "password": "Adm1nPass!"}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}
