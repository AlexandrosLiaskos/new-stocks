"""
HTTPX-based EODHD client.

One process-wide singleton (`get_client()`); reuses connections, applies a
sane retry policy on transient errors, and surfaces a typed `EODHDError`
on permanent failures.

The token is read from env at first use. Pass `api_token="demo"` for
sample-only access during development.
"""
from __future__ import annotations
import logging
import os
import time
from typing import Any
import httpx

log = logging.getLogger("eodhd")

DEFAULT_BASE = "https://eodhd.com/api"
DEFAULT_TIMEOUT = 15.0


class EODHDError(RuntimeError):
    """Raised for non-retryable API errors (auth, 4xx, malformed JSON)."""

    def __init__(self, message: str, *, status: int | None = None, url: str | None = None):
        super().__init__(message)
        self.status = status
        self.url = url


class EODHDClient:
    """Thin typed wrapper around the EODHD JSON API."""

    def __init__(self, api_token: str | None = None, base_url: str = DEFAULT_BASE,
                 timeout: float = DEFAULT_TIMEOUT) -> None:
        self.api_token = api_token or os.environ.get("EODHD_API_KEY") or "demo"
        self.base_url = base_url.rstrip("/")
        self._http = httpx.Client(
            timeout=timeout,
            follow_redirects=True,
            headers={"Accept": "application/json", "User-Agent": "new-stocks/1.0"},
        )

    # -------------------------------------------------------------- core

    def get(self, path: str, params: dict[str, Any] | None = None,
            *, retries: int = 2) -> Any:
        """GET {base}/{path}.json with auth + retry. Returns parsed JSON."""
        params = dict(params or {})
        params.setdefault("api_token", self.api_token)
        params.setdefault("fmt", "json")
        url = f"{self.base_url}/{path.lstrip('/')}"

        last_exc: Exception | None = None
        for attempt in range(retries + 1):
            try:
                r = self._http.get(url, params=params)
                if r.status_code == 200:
                    return r.json()
                if r.status_code in (401, 403):
                    raise EODHDError(
                        f"auth error ({r.status_code}) — check EODHD_API_KEY",
                        status=r.status_code, url=url,
                    )
                if r.status_code == 404:
                    # Many endpoints return 404 for "no data" rather than 200+empty
                    return None
                if 500 <= r.status_code < 600 or r.status_code == 429:
                    log.warning("EODHD %s %s — retry %d/%d", r.status_code, path, attempt + 1, retries)
                    last_exc = EODHDError(f"server {r.status_code}", status=r.status_code, url=url)
                else:
                    raise EODHDError(
                        f"HTTP {r.status_code}: {r.text[:200]}",
                        status=r.status_code, url=url,
                    )
            except (httpx.ReadTimeout, httpx.ConnectTimeout, httpx.RemoteProtocolError) as e:
                log.warning("EODHD timeout/network on %s — retry %d/%d: %s",
                            path, attempt + 1, retries, e)
                last_exc = e
            time.sleep(0.5 * (attempt + 1))

        if isinstance(last_exc, EODHDError):
            raise last_exc
        raise EODHDError(f"network error after {retries + 1} attempts: {last_exc}", url=url)

    def close(self) -> None:
        self._http.close()


# ---------------------------------------------------------- module-level singleton

_singleton: EODHDClient | None = None


def get_client() -> EODHDClient:
    """Process-wide singleton client. Lazy-initialises on first call."""
    global _singleton
    if _singleton is None:
        _singleton = EODHDClient()
    return _singleton
