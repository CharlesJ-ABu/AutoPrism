"""Credential-ephemeral, auditable source discovery providers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any
from urllib.parse import parse_qsl, urlsplit, urlunsplit

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.evidence import sha256_bytes, sha256_json
from app.models.sources import (
    SourceDiscoveryCandidate,
    SourceDiscoveryRun,
    SourcePool,
    utcnow,
)


GOOGLE_DISCOVERY_PROVIDER = "google-programmable-search-v1"
GOOGLE_DISCOVERY_ENDPOINT = "https://customsearch.googleapis.com/customsearch/v1"


class SearchDiscoveryError(ValueError):
    """A safe user-facing provider failure with no credential material."""


@dataclass(frozen=True)
class DiscoveryCandidate:
    title: str
    url: str
    display_host: str
    snippet: str
    mime_type: str | None
    suggested_kind: str

    def frozen_payload(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "display_host": self.display_host,
            "snippet": self.snippet,
            "mime_type": self.mime_type,
            "suggested_kind": self.suggested_kind,
        }


def discovery_run_integrity_valid(
    run: SourceDiscoveryRun,
    candidates: list[SourceDiscoveryCandidate],
) -> bool:
    ordered = sorted(candidates, key=lambda item: item.ordinal)
    if run.result_count != len(ordered):
        return False
    if [item.ordinal for item in ordered] != list(range(len(ordered))):
        return False
    if any(
        item.url_sha256 != sha256_bytes(item.url.encode("utf-8")) for item in ordered
    ):
        return False
    payload = [
        {
            "title": item.title,
            "url": item.url,
            "display_host": item.display_host,
            "snippet": item.snippet,
            "mime_type": item.mime_type,
            "suggested_kind": item.suggested_kind,
        }
        for item in ordered
    ]
    return run.result_hash == sha256_json(payload)


def normalize_candidate_url(value: Any) -> tuple[str, str]:
    if not isinstance(value, str) or not value.strip() or len(value) > 8000:
        raise SearchDiscoveryError("search result URL is missing")
    parsed = urlsplit(value.strip())
    if (
        parsed.scheme.lower() not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise SearchDiscoveryError("search result URL is not a safe HTTP(S) URL")
    try:
        hostname = parsed.hostname.encode("idna").decode("ascii").lower()
    except UnicodeError as exc:
        raise SearchDiscoveryError("search result hostname is invalid") from exc
    try:
        port = parsed.port
    except ValueError as exc:
        raise SearchDiscoveryError("search result port is invalid") from exc
    sensitive_query_keys = {
        "access_token",
        "api_key",
        "apikey",
        "auth",
        "key",
        "password",
        "signature",
        "token",
    }
    query_keys = {key.lower() for key, _ in parse_qsl(parsed.query)}
    if query_keys & sensitive_query_keys or any(
        key.startswith("x-amz-") for key in query_keys
    ):
        raise SearchDiscoveryError("search result URL contains credential-like query data")
    default_port = (parsed.scheme.lower() == "http" and port == 80) or (
        parsed.scheme.lower() == "https" and port == 443
    )
    authority = hostname if port is None or default_port else f"{hostname}:{port}"
    path = parsed.path or "/"
    normalized = urlunsplit(
        (parsed.scheme.lower(), authority, path, parsed.query, "")
    )
    return normalized, hostname


def infer_source_kind(url: str, mime_type: str | None) -> str:
    mime = (mime_type or "").lower()
    suffix = PurePosixPath(urlsplit(url).path).suffix.lower()
    if mime == "application/pdf" or suffix == ".pdf":
        return "pdf"
    if mime in {"text/csv", "application/csv"} or suffix == ".csv":
        return "csv"
    if (
        mime
        in {
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }
        or suffix in {".xls", ".xlsx"}
    ):
        return "xlsx"
    if mime in {"application/rss+xml", "application/atom+xml"} or suffix in {
        ".rss",
        ".atom",
    }:
        return "rss"
    return "html"


class GoogleProgrammableSearchProvider:
    def __init__(self, client: httpx.AsyncClient | None = None):
        self.client = client

    async def discover(
        self,
        *,
        api_key: str,
        search_engine_id: str,
        query: str,
        limit: int,
        start: int,
        safe: str,
    ) -> list[DiscoveryCandidate]:
        api_key = api_key.strip()
        search_engine_id = search_engine_id.strip()
        query = query.strip()
        if not api_key or not search_engine_id:
            raise SearchDiscoveryError("Google API key and search engine ID are required")
        if not query:
            raise SearchDiscoveryError("discovery query is required")
        client = self.client or httpx.AsyncClient(timeout=20, follow_redirects=False)
        owned_client = self.client is None
        try:
            try:
                response = await client.get(
                    GOOGLE_DISCOVERY_ENDPOINT,
                    params={
                        "key": api_key,
                        "cx": search_engine_id,
                        "q": query,
                        "num": limit,
                        "start": start,
                        "safe": safe,
                    },
                )
                response.raise_for_status()
            except httpx.TimeoutException:
                raise SearchDiscoveryError("Google search request timed out") from None
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                message = {
                    400: "Google rejected the search parameters",
                    401: "Google rejected the supplied API credential",
                    403: "Google denied this search engine or API credential",
                    429: "Google search quota or rate limit was reached",
                }.get(status, "Google search provider returned an error")
                raise SearchDiscoveryError(message) from None
            except httpx.RequestError:
                raise SearchDiscoveryError("Google search provider is unavailable") from None
            try:
                payload = response.json()
            except ValueError as exc:
                raise SearchDiscoveryError("Google search response was not JSON") from exc
            if not isinstance(payload, dict):
                raise SearchDiscoveryError("Google search response was malformed")
            raw_items = payload.get("items", [])
            if not isinstance(raw_items, list):
                raise SearchDiscoveryError("Google search result list was malformed")
            candidates: list[DiscoveryCandidate] = []
            seen_urls: set[str] = set()
            for item in raw_items:
                if not isinstance(item, dict):
                    continue
                try:
                    url, hostname = normalize_candidate_url(item.get("link"))
                except SearchDiscoveryError:
                    continue
                if url in seen_urls:
                    continue
                title = item.get("title")
                snippet = item.get("snippet", "")
                if not isinstance(title, str) or not title.strip():
                    continue
                if not isinstance(snippet, str):
                    snippet = ""
                mime_type = item.get("mime")
                mime_type = mime_type if isinstance(mime_type, str) else None
                candidates.append(
                    DiscoveryCandidate(
                        title=title.strip()[:1000],
                        url=url,
                        display_host=hostname,
                        snippet=snippet.strip()[:4000],
                        mime_type=mime_type,
                        suggested_kind=infer_source_kind(url, mime_type),
                    )
                )
                seen_urls.add(url)
                if len(candidates) >= limit:
                    break
            return candidates
        finally:
            if owned_client:
                await client.aclose()


class SearchDiscoveryService:
    def __init__(
        self,
        db: AsyncSession,
        provider: GoogleProgrammableSearchProvider | None = None,
    ):
        self.db = db
        self.provider = provider or GoogleProgrammableSearchProvider()

    async def discover_google(
        self,
        *,
        pool: SourcePool,
        api_key: str,
        search_engine_id: str,
        query: str,
        limit: int,
        start: int,
        safe: str,
    ) -> tuple[SourceDiscoveryRun, list[SourceDiscoveryCandidate]]:
        requested_at = utcnow()
        results = await self.provider.discover(
            api_key=api_key,
            search_engine_id=search_engine_id,
            query=query,
            limit=limit,
            start=start,
            safe=safe,
        )
        completed_at = utcnow()
        config_payload = {
            "engine_id_sha256": sha256_bytes(search_engine_id.encode("utf-8")),
            "limit": limit,
            "safe": safe,
            "start": start,
        }
        frozen_results = [item.frozen_payload() for item in results]
        run = SourceDiscoveryRun(
            pool_id=pool.id,
            provider=GOOGLE_DISCOVERY_PROVIDER,
            query=query,
            provider_config_hash=sha256_json(config_payload),
            result_count=len(results),
            result_hash=sha256_json(frozen_results),
            requested_at=requested_at,
            completed_at=completed_at,
        )
        self.db.add(run)
        await self.db.flush()
        candidates = [
            SourceDiscoveryCandidate(
                run_id=run.id,
                ordinal=ordinal,
                title=item.title,
                url=item.url,
                url_sha256=sha256_bytes(item.url.encode("utf-8")),
                display_host=item.display_host,
                snippet=item.snippet,
                mime_type=item.mime_type,
                suggested_kind=item.suggested_kind,
                created_at=completed_at,
            )
            for ordinal, item in enumerate(results)
        ]
        self.db.add_all(candidates)
        await self.db.commit()
        return run, candidates
