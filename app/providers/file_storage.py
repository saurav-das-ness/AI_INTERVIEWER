"""Local file storage adapter for upload provenance."""

from __future__ import annotations

import re
import uuid
from pathlib import Path


SAFE_NAME_PATTERN = re.compile(r"[^a-zA-Z0-9._-]+")


class LocalFileStorage:
    """Persist uploaded files locally so ingestion provenance can be traced later."""

    def __init__(self, base_dir: str) -> None:
        self._base_dir = Path(base_dir)
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def save_upload(self, file_name: str, content: bytes, namespace: str = "imports") -> str:
        """Persist uploaded bytes and return the local storage path."""

        safe_name = SAFE_NAME_PATTERN.sub("_", file_name).strip("._") or "upload.bin"
        target_dir = self._base_dir / namespace
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / f"{uuid.uuid4()}_{safe_name}"
        target_path.write_bytes(content)
        return str(target_path)
