"""OpenAI-compatible LLM client helpers with provider fallback."""

import logging
from dataclasses import dataclass
from typing import Any, Iterable, Optional

import instructor
from openai import AsyncOpenAI

from app.config import settings as global_settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LLMProvider:
    name: str
    api_key: str
    model: str
    base_url: Optional[str]
    json_mode: bool


class _FallbackCompletions:
    def __init__(self, providers: Iterable[LLMProvider]):
        self._providers = list(providers)
        self._clients: dict[str, Any] = {}

    def _client_for(self, provider: LLMProvider):
        if provider.name not in self._clients:
            base_client = AsyncOpenAI(
                api_key=provider.api_key,
                base_url=provider.base_url,
            )
            if provider.json_mode:
                self._clients[provider.name] = instructor.from_openai(
                    base_client,
                    mode=instructor.Mode.JSON,
                )
            else:
                self._clients[provider.name] = instructor.from_openai(base_client)
        return self._clients[provider.name]

    async def create(self, **kwargs):
        last_error = None
        for index, provider in enumerate(self._providers):
            request_kwargs = dict(kwargs)
            request_kwargs["model"] = provider.model
            if provider.name == "groq" and request_kwargs.get("max_tokens", 0) > 1500:
                request_kwargs["max_tokens"] = 1500
            try:
                return await self._client_for(provider).chat.completions.create(
                    **request_kwargs
                )
            except Exception as exc:
                last_error = exc
                if index >= len(self._providers) - 1:
                    break
                logger.warning(
                    "LLM provider %s failed, falling back to %s: %s",
                    provider.name,
                    self._providers[index + 1].name,
                    exc,
                )
        raise last_error


class _FallbackChat:
    def __init__(self, providers: Iterable[LLMProvider]):
        self.completions = _FallbackCompletions(providers)


class FallbackLLMClient:
    def __init__(self, providers: Iterable[LLMProvider]):
        self.chat = _FallbackChat(providers)


def _provider_specs() -> list[LLMProvider]:
    provider = (global_settings.LLM_PROVIDER or "openai").lower()
    specs: list[LLMProvider] = []

    if provider == "openrouter":
        specs.append(
            LLMProvider(
                name="openrouter",
                api_key=global_settings.OPENROUTER_API_KEY,
                model=global_settings.LLM_MODEL or global_settings.OPENROUTER_LLM_MODEL,
                base_url=global_settings.OPENROUTER_BASE_URL,
                json_mode=True,
            )
        )
        if global_settings.GROQ_API_KEY:
            specs.append(
                LLMProvider(
                    name="groq",
                    api_key=global_settings.GROQ_API_KEY,
                    model=global_settings.GROQ_LLM_MODEL,
                    base_url="https://api.groq.com/openai/v1",
                    json_mode=True,
                )
            )
    elif provider == "shopaikey":
        specs.append(
            LLMProvider(
                name="shopaikey",
                api_key=global_settings.OPENAI_API_KEY,
                model=global_settings.LLM_MODEL,
                base_url="https://api.shopaikey.com/v1",
                json_mode=True,
            )
        )
        if global_settings.OPENROUTER_API_KEY:
            specs.append(
                LLMProvider(
                    name="openrouter",
                    api_key=global_settings.OPENROUTER_API_KEY,
                    model=global_settings.OPENROUTER_LLM_MODEL,
                    base_url=global_settings.OPENROUTER_BASE_URL,
                    json_mode=True,
                )
            )
        if global_settings.GROQ_API_KEY:
            specs.append(
                LLMProvider(
                    name="groq",
                    api_key=global_settings.GROQ_API_KEY,
                    model=global_settings.GROQ_LLM_MODEL,
                    base_url="https://api.groq.com/openai/v1",
                    json_mode=True,
                )
            )
    elif provider == "groq":
        specs.append(
            LLMProvider(
                name="groq",
                api_key=global_settings.GROQ_API_KEY,
                model=global_settings.LLM_MODEL or global_settings.GROQ_LLM_MODEL,
                base_url="https://api.groq.com/openai/v1",
                json_mode=True,
            )
        )
    else:
        specs.append(
            LLMProvider(
                name="openai",
                api_key=global_settings.OPENAI_API_KEY,
                model=global_settings.LLM_MODEL,
                base_url=None,
                json_mode=False,
            )
        )
        if global_settings.GROQ_API_KEY:
            specs.append(
                LLMProvider(
                    name="groq",
                    api_key=global_settings.GROQ_API_KEY,
                    model=global_settings.GROQ_LLM_MODEL,
                    base_url="https://api.groq.com/openai/v1",
                    json_mode=True,
                )
            )

    return [spec for spec in specs if spec.api_key]


def build_llm_client() -> FallbackLLMClient:
    providers = _provider_specs()
    if not providers:
        raise RuntimeError("No LLM provider API key configured")
    return FallbackLLMClient(providers)
