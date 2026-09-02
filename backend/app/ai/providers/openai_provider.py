from openai import AsyncOpenAI
from pydantic import BaseModel

from app.ai.providers.base import T, AIProvider


class OpenAIProvider(AIProvider):
    def __init__(self, api_key: str, model: str) -> None:
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model

    async def chat(self, system_prompt: str, history: list[dict[str, str]]) -> str:
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "system", "content": system_prompt}, *history],
        )
        return response.choices[0].message.content or ""

    async def structured(self, system_prompt: str, user_prompt: str, response_model: type[T]) -> T:
        response = await self._client.beta.chat.completions.parse(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format=response_model,
        )
        return self._require_parsed(response)

    async def analyze_image(self, system_prompt: str, image_url: str, response_model: type[T]) -> T:
        response = await self._client.beta.chat.completions.parse(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Analyze this meal photo."},
                        {"type": "image_url", "image_url": {"url": image_url}},
                    ],
                },
            ],
            response_format=response_model,
        )
        return self._require_parsed(response)

    @staticmethod
    def _require_parsed(response) -> T:
        parsed = response.choices[0].message.parsed
        if parsed is None:
            # .parse() leaves this null on a refusal or a schema the model couldn't satisfy —
            # surfacing it as a validation error keeps the caller's error handling in one place
            # rather than needing a separate null-check at every call site.
            raise ValueError("Model returned no parseable structured output")
        assert isinstance(parsed, BaseModel)
        return parsed  # type: ignore[return-value]
