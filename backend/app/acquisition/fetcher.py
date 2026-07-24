from __future__ import annotations

from datetime import datetime, timezone

import httpx

from app.acquisition.contracts import AcquisitionBlocked, FetchRequest, FetchResult


DEFAULT_USER_AGENT = "AutoPrism/2.0 (+local research evidence collector)"


class HttpFetcher:
    async def fetch(self, request: FetchRequest) -> FetchResult:
        headers = {"User-Agent": DEFAULT_USER_AGENT, **dict(request.headers)}
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=request.timeout_seconds,
        ) as client:
            async with client.stream("GET", request.url, headers=headers) as response:
                if response.status_code in {401, 403, 407, 429}:
                    raise AcquisitionBlocked(
                        "ACCESS_BLOCKED",
                        f"Source returned HTTP {response.status_code}",
                    )
                response.raise_for_status()
                chunks: list[bytes] = []
                size = 0
                async for chunk in response.aiter_bytes():
                    size += len(chunk)
                    if size > request.max_bytes:
                        raise AcquisitionBlocked(
                            "MAX_BYTES_EXCEEDED",
                            f"Source exceeded {request.max_bytes} bytes",
                        )
                    chunks.append(chunk)

                content_type = response.headers.get("content-type", "application/octet-stream")
                media_type = content_type.split(";", 1)[0].strip().lower()
                return FetchResult(
                    requested_url=request.url,
                    final_url=str(response.url),
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    content=b"".join(chunks),
                    retrieved_at=datetime.now(timezone.utc).replace(tzinfo=None),
                    media_type=media_type,
                )
