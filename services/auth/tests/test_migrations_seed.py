import os
import subprocess
import sys


def test_alembic_upgrade_and_seed(tmp_path):
    env = {**os.environ, "DATABASE_URL": f"sqlite:///{tmp_path}/auth.db", "SEED_DATA": "true", "ADMIN_EMAIL": "root@example.com", "ADMIN_PASSWORD": "SeedPass123", "DEMO_USER_EMAIL": "demo@example.com", "DEMO_USER_PASSWORD": "DemoPass123"}
    for cmd in (["alembic", "upgrade", "head"], [sys.executable, "-m", "app.seed"], [sys.executable, "-m", "app.seed"]):
        res = subprocess.run(cmd if cmd[0] != "alembic" else [sys.executable, "-m", "alembic", "upgrade", "head"], env=env, capture_output=True, text=True)
        assert res.returncode == 0, res.stderr
    import sqlite3

    rows = sqlite3.connect(tmp_path / "auth.db").execute("select email, role from users order by id").fetchall()
    assert rows == [("root@example.com", "admin"), ("demo@example.com", "user")]
