from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping


@dataclass(frozen=True)
class FetchRequest:
    url: str
    headers: Mapping[str, str] = field(default_factory=dict)
    timeout_seconds: float = 30.0
    max_bytes: int = 25 * 1024 * 1024


@dataclass(frozen=True)
class FetchResult:
    requested_url: str
    final_url: str
    status_code: int
    headers: Mapping[str, str]
    content: bytes
    retrieved_at: datetime
    media_type: str


@dataclass(frozen=True)
class ParsedRecord:
    locator_type: str
    locator: Mapping[str, Any]
    text: str
    fields: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ParseResult:
    media_type: str
    title: str | None
    published_at: datetime | None
    records: tuple[ParsedRecord, ...]
    metadata: Mapping[str, Any] = field(default_factory=dict)


class AcquisitionBlocked(RuntimeError):
    def __init__(self, reason_code: str, message: str):
        super().__init__(message)
        self.reason_code = reason_code
