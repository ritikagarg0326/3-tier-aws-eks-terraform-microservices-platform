import os
import sqlite3
import subprocess
import sys


def test_alembic_upgrade(tmp_path):
    env = {**os.environ, "DATABASE_URL": f"sqlite:///{tmp_path}/v.db"}
    res = subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], env=env, capture_output=True, text=True)
    assert res.returncode == 0, res.stderr
    assert "media_assets" in {r[0] for r in sqlite3.connect(tmp_path / "v.db").execute("select name from sqlite_master")}
