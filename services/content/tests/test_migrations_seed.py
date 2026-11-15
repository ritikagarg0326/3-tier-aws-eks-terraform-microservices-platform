import os
import sqlite3
import subprocess
import sys


def test_migrate_and_seed_idempotent(tmp_path):
    env = {**os.environ, "DATABASE_URL": f"sqlite:///{tmp_path}/c.db"}
    for cmd in ([sys.executable, "-m", "alembic", "upgrade", "head"], [sys.executable, "-m", "app.seed"], [sys.executable, "-m", "app.seed"]):
        res = subprocess.run(cmd, env=env, capture_output=True, text=True)
        assert res.returncode == 0, res.stderr
    assert sqlite3.connect(tmp_path / "c.db").execute("select count(*) from contents").fetchone()[0] == 12
