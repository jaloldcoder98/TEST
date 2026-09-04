"""Thin HTTP client to the FastAPI backend. The bot has no business logic and no direct DB
access (spec.md §30/§61 rule 11) — every method here is just a call to one of docs/API.md's
endpoints; all state (workouts, sets, food logs, progress) lives on the backend exactly like it
does for the web app, so the same account sees the same data on both surfaces.
"""

from __future__ import annotations

from typing import Any

import httpx

from config import settings


class BackendAPIError(Exception):
    """Mirrors the backend's {"success": false, "error": {"code", "message"}} shape so handlers
    can react to a specific code (e.g. WORKOUT_HAS_HISTORY) instead of a generic failure."""

    def __init__(self, code: str, message: str, status_code: int) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(f"{code}: {message}")


class BackendClient:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(base_url=settings.backend_api_url, timeout=30.0)

    async def close(self) -> None:
        await self._client.aclose()

    async def _request(self, method: str, path: str, token: str | None = None, **kwargs: Any) -> Any:
        headers = kwargs.pop("headers", {}) or {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        # Sent on every call rather than only the two that need it: it identifies the caller as
        # this bot, and the endpoints that do not check it simply ignore it (D-20).
        if settings.bot_shared_secret:
            headers["X-Bot-Secret"] = settings.bot_shared_secret
        response = await self._client.request(method, path, headers=headers, **kwargs)
        if response.status_code >= 400:
            try:
                body = response.json()
                error = body.get("error", {})
                code, message = error.get("code", "UNKNOWN_ERROR"), error.get("message", "Request failed")
            except ValueError:
                code, message = "UNKNOWN_ERROR", f"Request failed with status {response.status_code}"
            raise BackendAPIError(code, message, response.status_code)
        if response.status_code == 204 or not response.content:
            return None
        return response.json()

    async def health(self) -> dict:
        return await self._request("GET", "/health")

    # --- Auth -----------------------------------------------------------------------------

    async def telegram_auth(
        self, telegram_id: int, chat_id: int, telegram_username: str | None, first_name: str | None, language: str
    ) -> dict:
        return await self._request(
            "POST",
            "/auth/telegram",
            json={
                "telegram_id": telegram_id,
                "chat_id": chat_id,
                "telegram_username": telegram_username,
                "first_name": first_name,
                "language": language,
            },
        )

    async def refresh(self, refresh_token: str) -> dict:
        """The bot's own rotation endpoint. `/auth/refresh` is the browser's and reads an httpOnly
        cookie the bot does not have, so the token travels in the body here instead (D-13)."""
        return await self._request("POST", "/auth/bot/refresh", json={"refresh_token": refresh_token})


    # --- Users ------------------------------------------------------------------------------

    async def get_me(self, token: str) -> dict:
        return await self._request("GET", "/users/me", token=token)

    async def update_me(self, token: str, payload: dict) -> dict:
        return await self._request("PATCH", "/users/me", token=token, json=payload)

    # --- Exercises --------------------------------------------------------------------------

    async def list_exercises(self, token: str | None, **params: Any) -> dict:
        return await self._request("GET", "/exercises", token=token, params={k: v for k, v in params.items() if v})

    async def get_exercise(self, token: str | None, exercise_id: str, lang: str) -> dict:
        return await self._request("GET", f"/exercises/{exercise_id}", token=token, params={"lang": lang})

    async def muscles(self) -> list[dict]:
        return await self._request("GET", "/exercises/muscles")

    # --- Workouts ---------------------------------------------------------------------------

    async def list_workouts(self, token: str) -> list[dict]:
        return await self._request("GET", "/workouts", token=token)

    async def get_workout(self, token: str, workout_id: str) -> dict:
        return await self._request("GET", f"/workouts/{workout_id}", token=token)

    async def create_workout(self, token: str, payload: dict) -> dict:
        return await self._request("POST", "/workouts", token=token, json=payload)

    async def delete_workout(self, token: str, workout_id: str) -> None:
        await self._request("DELETE", f"/workouts/{workout_id}", token=token)

    async def start_workout(self, token: str, workout_id: str) -> dict:
        return await self._request("POST", f"/workouts/{workout_id}/start", token=token)

    async def log_set(self, token: str, session_id: str, payload: dict) -> dict:
        return await self._request("POST", f"/workout-sessions/{session_id}/sets", token=token, json=payload)

    async def finish_session(self, token: str, session_id: str) -> dict:
        return await self._request("POST", f"/workout-sessions/{session_id}/finish", token=token)

    # --- Nutrition --------------------------------------------------------------------------

    async def log_food(self, token: str, payload: dict) -> dict:
        return await self._request("POST", "/nutrition/log", token=token, json=payload)

    async def today_nutrition(self, token: str) -> dict:
        return await self._request("GET", "/nutrition/today", token=token)

    # --- Progress ---------------------------------------------------------------------------

    async def progress_summary(self, token: str) -> dict:
        return await self._request("GET", "/progress", token=token)

    async def log_weight(self, token: str, weight_kg: float) -> dict:
        return await self._request("POST", "/progress/weight", token=token, json={"weight_kg": weight_kg})

    # --- AI ---------------------------------------------------------------------------------

    async def ai_chat(self, token: str, message: str, conversation_id: str | None) -> dict:
        payload: dict[str, Any] = {"message": message}
        if conversation_id:
            payload["conversation_id"] = conversation_id
        return await self._request("POST", "/ai/chat", token=token, json=payload)


backend = BackendClient()
