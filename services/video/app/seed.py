"""Idempotent seed: uploads bundled sample posters and a sample video for the seeded catalogue.

Assets live in seed_assets/: poster_<n>.jpg for content id n, and sample.mp4 (used as the video for each).
"""
import io
import logging
import re
import time
import uuid
from pathlib import Path

from hotstar_common.logging import setup_logging
from sqlalchemy import select

from .config import get_settings
from .db import SessionLocal
from .models import MediaAsset
from .storage import get_storage


def seed() -> None:
    log = logging.getLogger("seed")
    s = get_settings()
    folder = Path(s.seed_assets_dir)
    posters = {int(m.group(1)): p for p in folder.glob("poster_*.jpg") if (m := re.fullmatch(r"poster_(\d+)\.jpg", p.name))}
    sample = folder / "sample.mp4"
    if not posters:
        log.info("no seed assets found; skipping")
        return
    storage = get_storage()
    for attempt in range(10):
        try:
            storage.ensure_ready()
            break
        except Exception as exc:  # noqa: BLE001
            log.warning("storage not ready: %s", exc)
            time.sleep(3)
    created = 0
    with SessionLocal() as db:
        for cid, poster in sorted(posters.items()):
            have = {a.kind for a in db.scalars(select(MediaAsset).where(MediaAsset.content_id == cid))}
            plan = [("poster", poster, "image/jpeg", ".jpg"), ("thumbnail", poster, "image/jpeg", ".jpg")]
            if sample.exists():
                plan.append(("video", sample, "video/mp4", ".mp4"))
            for kind, path, ctype, ext in plan:
                if kind in have:
                    continue
                key = f"content/{cid}/{kind}/{uuid.uuid4().hex}{ext}"
                data = path.read_bytes()
                storage.put(key, io.BytesIO(data), ctype)
                db.add(MediaAsset(content_id=cid, kind=kind, object_key=key, content_type=ctype, size_bytes=len(data), original_filename=path.name))
                created += 1
        db.commit()
    log.info("seeded %d media assets", created)


if __name__ == "__main__":
    setup_logging("video-seed")
    seed()
