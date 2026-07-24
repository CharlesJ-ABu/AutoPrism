"""Content-addressed artifact storage for V2 local mode."""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from app.domain.evidence import sha256_bytes, validate_sha256


@dataclass(frozen=True)
class StoredArtifact:
    sha256: str
    byte_size: int
    storage_uri: str


class LocalArtifactStore:
    def __init__(self, root: str | Path):
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def path_for(self, sha256: str) -> Path:
        digest = validate_sha256(sha256)
        return self.root / digest[:2] / digest[2:4] / digest

    def put(self, content: bytes) -> StoredArtifact:
        if not isinstance(content, bytes):
            raise TypeError("artifact content must be bytes")
        digest = sha256_bytes(content)
        destination = self.path_for(digest)
        destination.parent.mkdir(parents=True, exist_ok=True)

        if destination.exists():
            existing = destination.read_bytes()
            if sha256_bytes(existing) != digest:
                raise ValueError(f"artifact integrity check failed: {digest}")
        else:
            file_descriptor, temporary_name = tempfile.mkstemp(
                prefix=".artifact-",
                dir=destination.parent,
            )
            try:
                with os.fdopen(file_descriptor, "wb") as temporary_file:
                    temporary_file.write(content)
                    temporary_file.flush()
                    os.fsync(temporary_file.fileno())
                os.replace(temporary_name, destination)
            finally:
                if os.path.exists(temporary_name):
                    os.unlink(temporary_name)

        return StoredArtifact(
            sha256=digest,
            byte_size=len(content),
            storage_uri=destination.as_uri(),
        )

    def read(self, sha256: str) -> bytes:
        content = self.path_for(sha256).read_bytes()
        if sha256_bytes(content) != validate_sha256(sha256):
            raise ValueError(f"artifact integrity check failed: {sha256}")
        return content
