"""Storage abstraction. S3Storage works with MinIO (local) and AWS S3 (cloud); LocalStorage is for dev/tests."""
import os
import shutil
from abc import ABC, abstractmethod
from collections.abc import Iterator
from functools import lru_cache
from pathlib import Path
from typing import BinaryIO

from .config import get_settings

CHUNK = 1024 * 1024


class ObjectNotFound(Exception):
    pass


class Storage(ABC):
    @abstractmethod
    def ensure_ready(self) -> None: ...

    @abstractmethod
    def put(self, key: str, fileobj: BinaryIO, content_type: str) -> None: ...

    @abstractmethod
    def size(self, key: str) -> int: ...

    @abstractmethod
    def read_range(self, key: str, start: int, end: int) -> Iterator[bytes]:
        """Yield bytes start..end (inclusive)."""

    @abstractmethod
    def delete(self, key: str) -> None: ...

    @abstractmethod
    def ping(self) -> None: ...


class S3Storage(Storage):
    def __init__(self, *, bucket: str, endpoint_url: str, region: str, access_key: str, secret_key: str):
        import boto3
        from botocore.config import Config

        kwargs: dict = {"region_name": region, "config": Config(signature_version="s3v4", s3={"addressing_style": "path" if endpoint_url else "auto"}, retries={"max_attempts": 3, "mode": "standard"})}
        if endpoint_url:
            kwargs["endpoint_url"] = endpoint_url
        if access_key and secret_key:
            kwargs.update(aws_access_key_id=access_key, aws_secret_access_key=secret_key)
        self.client = boto3.client("s3", **kwargs)
        self.bucket = bucket

    def ensure_ready(self) -> None:
        from botocore.exceptions import ClientError

        try:
            self.client.head_bucket(Bucket=self.bucket)
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in ("404", "NoSuchBucket", "NotFound"):
                self.client.create_bucket(Bucket=self.bucket)
            else:
                raise

    def put(self, key, fileobj, content_type):
        self.client.upload_fileobj(fileobj, self.bucket, key, ExtraArgs={"ContentType": content_type})

    def size(self, key):
        from botocore.exceptions import ClientError

        try:
            return int(self.client.head_object(Bucket=self.bucket, Key=key)["ContentLength"])
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in ("404", "NoSuchKey", "NotFound"):
                raise ObjectNotFound(key)
            raise

    def read_range(self, key, start, end):
        body = self.client.get_object(Bucket=self.bucket, Key=key, Range=f"bytes={start}-{end}")["Body"]
        try:
            yield from body.iter_chunks(CHUNK)
        finally:
            body.close()

    def delete(self, key):
        self.client.delete_object(Bucket=self.bucket, Key=key)

    def ping(self):
        self.client.head_bucket(Bucket=self.bucket)


class LocalStorage(Storage):
    def __init__(self, root: str):
        self.root = Path(root)

    def _path(self, key: str) -> Path:
        p = (self.root / key).resolve()
        if self.root.resolve() not in p.parents:
            raise ValueError("invalid key")
        return p

    def ensure_ready(self):
        self.root.mkdir(parents=True, exist_ok=True)

    def put(self, key, fileobj, content_type):
        p = self._path(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "wb") as out:
            shutil.copyfileobj(fileobj, out, CHUNK)

    def size(self, key):
        try:
            return os.path.getsize(self._path(key))
        except FileNotFoundError:
            raise ObjectNotFound(key)

    def read_range(self, key, start, end):
        remaining = end - start + 1
        with open(self._path(key), "rb") as f:
            f.seek(start)
            while remaining > 0:
                chunk = f.read(min(CHUNK, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
                yield chunk

    def delete(self, key):
        try:
            self._path(key).unlink()
        except FileNotFoundError:
            pass

    def ping(self):
        if not self.root.exists():
            raise RuntimeError("storage root missing")


@lru_cache
def get_storage() -> Storage:
    s = get_settings()
    if s.storage_backend == "local":
        return LocalStorage(s.local_storage_path)
    return S3Storage(bucket=s.s3_bucket, endpoint_url=s.s3_endpoint_url, region=s.s3_region, access_key=s.s3_access_key, secret_key=s.s3_secret_key)
