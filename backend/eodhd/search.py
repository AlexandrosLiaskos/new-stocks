"""Search — `/api/search/{query}`. Returns up to ~15 hits across all asset types."""
from __future__ import annotations
from typing import Any
from .client import get_client


def search(query: str, limit: int = 15) -> list[dict[str, Any]]:
    if not query or not query.strip():
        return []
    payload = get_client().get(f"search/{query.strip()}", {"limit": limit})
    return payload or []
