import os

os.environ.update(DATABASE_URL="sqlite://", JWT_SECRET="test-secret-test-secret-test-secret-0123456789")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from hotstar_common.db import Base  # noqa: E402
from hotstar_common.security import create_token  # noqa: E402

from app import media_client  # noqa: E402
from app.db import engine  # noqa: E402
from app.main import app  # noqa: E402


def headers_for(uid=1, role="user"):
    tok = create_token({"sub": str(uid), "email": "u@example.com", "username": "u", "role": role}, "access", 600)
    return {"Authorization": f"Bearer {tok}"}


@pytest.fixture(autouse=True)
def _schema(monkeypatch):
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    monkeypatch.setattr(media_client, "delete_media", lambda cid, auth: DELETED.append(cid) or True)
    DELETED.clear()


DELETED: list = []


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def user_h():
    return headers_for(2, "user")


@pytest.fixture
def admin_h():
    return headers_for(1, "admin")
