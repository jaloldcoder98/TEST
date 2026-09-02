"""The AIProvider abstraction (spec.md §61 rule: never call an AI SDK directly from a route or
service — always go through this interface). This is what makes swapping OpenAI for another
model provider later a one-file change instead of a rewrite, and what makes ai_service.py
testable with a stub provider instead of a real API key.
"""

from abc import ABC, abstractmethod
from typing import TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class AIProvider(ABC):
    @abstractmethod
    async def chat(self, system_prompt: str, history: list[dict[str, str]]) -> str:
        """Plain-text completion for conversational use (AI Coach, nutrition Q&A). `history` is
        a list of {"role": "user"|"assistant", "content": str} in chronological order."""
        ...

    @abstractmethod
    async def structured(self, system_prompt: str, user_prompt: str, response_model: type[T]) -> T:
        """Completion constrained to `response_model`'s JSON schema, returned already parsed and
        Pydantic-validated (spec.md §61: all AI output must be validated before use)."""
        ...

    @abstractmethod
    async def analyze_image(self, system_prompt: str, image_url: str, response_model: type[T]) -> T:
        """Like `structured`, but with an image as the input (food-photo analysis)."""
        ...
