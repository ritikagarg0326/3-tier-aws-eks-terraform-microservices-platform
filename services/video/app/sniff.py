"""Validate uploads by magic bytes instead of trusting the client-supplied Content-Type."""
from typing import BinaryIO

# kind -> list of (content_type, extension)
def sniff(fileobj: BinaryIO) -> tuple[str, str] | None:
    fileobj.seek(0)
    head = fileobj.read(16)
    fileobj.seek(0)
    if len(head) >= 8 and head[4:8] == b"ftyp":
        return "video/mp4", ".mp4"
    if head[:4] == b"\x1a\x45\xdf\xa3":
        return "video/webm", ".webm"
    if head[:3] == b"\xff\xd8\xff":
        return "image/jpeg", ".jpg"
    if head[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png", ".png"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp", ".webp"
    return None


VIDEO_TYPES = {"video/mp4", "video/webm"}
IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
