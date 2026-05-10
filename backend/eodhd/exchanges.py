"""Exchanges list — `/api/exchanges-list`."""
from __future__ import annotations
from typing import Any
from .client import get_client


def list_exchanges() -> list[dict[str, Any]]:
    return get_client().get("exchanges-list/") or []
