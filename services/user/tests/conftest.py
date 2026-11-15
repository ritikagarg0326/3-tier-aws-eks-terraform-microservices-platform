import os

os.environ.update(DATABASE_URL="sqlite://", JWT_SECRET="test-secret-test-secret-test-secret-0123456789")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from hotstar_common.db import Base  # noqa: E402
from hotstar_common.security import create_token  # noqa: E402

from app.db import engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def _schema():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def headers_for(uid=1, role="user", username="viewer"):
    tok = create_token({"sub": str(uid), "email": f"u{uid}@example.com", "username": username, "role": role}, "access", 600)
    return {"Authorization": f"Bearer {tok}"}


@pytest.fixture
def h1():
    return headers_for(1)


@pytest.fixture
def h2():
    return headers_for(2, username="other")
