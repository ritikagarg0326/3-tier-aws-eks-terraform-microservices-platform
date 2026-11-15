import os

os.environ.update(DATABASE_URL="sqlite://", JWT_SECRET="test-secret-test-secret-test-secret-0123456789", STORAGE_BACKEND="local")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from hotstar_common.db import Base  # noqa: E402
from hotstar_common.security import create_token  # noqa: E402

from app.db import engine  # noqa: E402
from app.main import app  # noqa: E402
from app.storage import LocalStorage, get_storage  # noqa: E402

MP4 = b"\x00\x00\x00\x18ftypmp42" + bytes(range(256)) * 8  # 24 + 2048 bytes
PNG = b"\x89PNG\r\n\x1a\n" + b"x" * 100


def headers_for(uid=1, role="user"):
    tok = create_token({"sub": str(uid), "email": "u@example.com", "username": "u", "role": role}, "access", 600)
    return {"Authorization": f"Bearer {tok}"}


@pytest.fixture(autouse=True)
def _env(tmp_path):
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    storage = LocalStorage(str(tmp_path / "media"))
    storage.ensure_ready()
    app.dependency_overrides[get_storage] = lambda: storage
    yield storage
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def admin_h():
    return headers_for(1, "admin")


@pytest.fixture
def user_h():
    return headers_for(2, "user")
