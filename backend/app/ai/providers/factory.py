"""Single place that decides which AIProvider (if any) is active — every AI route depends on
`get_provider()` rather than importing OpenAIProvider directly, so "no key configured" is one
`if provider is None` check instead of scattered try/except blocks around SDK calls.
"""

from functools import lru_cache

from app.ai.providers.base import AIProvider
from app.ai.providers.openai_provider import OpenAIProvider
from app.core.config import get_settings


@lru_cache
def get_provider() -> AIProvider | None:
    settings = get_settings()
    if not settings.openai_api_key:
        return None
    return OpenAIProvider(api_key=settings.openai_api_key, model=settings.ai_model)
