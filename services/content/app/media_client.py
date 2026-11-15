"""Best-effort cleanup of stored media when content is deleted (service-to-service call)."""
import logging

import httpx

from .config import get_settings

log = logging.getLogger("media-client")


def delete_media(content_id: int, authorization: str | None) -> bool:
    url = f"{get_settings().video_service_url}/videos/media/{content_id}"
    try:
        r = httpx.delete(url, headers={"Authorization": authorization or ""}, timeout=10)
        if r.status_code >= 400:
            log.warning("media cleanup rejected", extra={"content_id": content_id, "status": r.status_code})
            return False
        return True
    except httpx.HTTPError as exc:
        log.warning("media cleanup failed", extra={"content_id": content_id, "error": str(exc)})
        return False
