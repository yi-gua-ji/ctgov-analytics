"""Async ClinicalTrials.gov v2 API client with retry, backoff and pacing."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx

from .config import Config

logger = logging.getLogger(__name__)


class CtgovError(RuntimeError):
    """Raised when the API cannot be reached after all retries."""


class CtgovClient:
    """Page through the v2 studies API for one search term at a time."""

    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg.api
        self._lock = asyncio.Lock()
        self._last = 0.0

    async def _pace(self) -> None:
        """Space requests according to rate_limit_per_sec."""
        if self.cfg.rate_limit_per_sec <= 0:
            return
        interval = 1.0 / self.cfg.rate_limit_per_sec
        async with self._lock:
            wait = self._last + interval - time.monotonic()
            if wait > 0:
                await asyncio.sleep(wait)
            self._last = time.monotonic()

    def _params(self, term: str, page_size: int, page_token: str | None, fields: list[str]) -> dict[str, Any]:
        params: dict[str, Any] = {"query.term": term, "pageSize": page_size, "format": "json"}
        if fields:
            params["fields"] = ",".join(fields)
        if page_token:
            params["pageToken"] = page_token
        return params

    async def fetch_page(
        self, term: str, page_size: int, page_token: str | None, fields: list[str]
    ) -> tuple[list[dict[str, Any]], str | None]:
        """Fetch one page of studies; returns (studies, next_page_token)."""
        last_error: Exception | None = None
        for attempt in range(1, self.cfg.max_retries + 1):
            await self._pace()
            try:
                async with httpx.AsyncClient(timeout=self.cfg.timeout) as client:
                    response = await client.get(
                        f"{self.cfg.base_url}/studies",
                        params=self._params(term, page_size, page_token, fields),
                    )
                if response.status_code in (429,) or response.status_code >= 500:
                    raise httpx.HTTPStatusError(
                        f"retryable status {response.status_code}",
                        request=response.request,
                        response=response,
                    )
                response.raise_for_status()
                body = response.json()
                studies = body.get("studies") or []
                next_token = body.get("nextPageToken")
                return studies, next_token
            except (httpx.HTTPStatusError, httpx.TransportError, httpx.TimeoutException) as exc:
                last_error = exc
                delay = min(2 ** attempt, 20)
                logger.warning("API page failed (attempt %d/%d): %s", attempt, self.cfg.max_retries, exc)
                if attempt < self.cfg.max_retries:
                    await asyncio.sleep(delay)
        raise CtgovError(f"ClinicalTrials.gov request failed after {self.cfg.max_retries} attempts: {last_error}")

    async def iter_studies(
        self, term: str, max_studies: int, page_size: int, fields: list[str]
    ):
        """Yield studies for a term until the cap or the end of results."""
        token: str | None = None
        fetched = 0
        while fetched < max_studies:
            studies, token = await self.fetch_page(term, page_size, token, fields)
            if not studies:
                return
            for study in studies:
                if fetched >= max_studies:
                    return
                fetched += 1
                yield study
            if not token:
                return