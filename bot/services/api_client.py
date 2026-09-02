"""Thin HTTP client to the FastAPI backend. The bot has no business logic and no direct DB
access (spec.md §30/§61 rule 11) — every action here is just a call to `docs/API.md`'s endpoints.
"""

import httpx

from config import settings


class BackendClient:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(base_url=settings.backend_api_url, timeout=30.0)

    async def health(self) -> dict:
        response = await self._client.get("/health")
        response.raise_for_status()
        return response.json()

    async def close(self) -> None:
        await self._client.aclose()


backend = BackendClient()
