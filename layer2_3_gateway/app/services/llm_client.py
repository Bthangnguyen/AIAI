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
            if provider.name == "groq":
                groq_max = getattr(global_settings, "GROQ_MAX_TOKENS", 1024)
                if "max_tokens" in request_kwargs and request_kwargs["max_tokens"] is not None:
                    request_kwargs["max_tokens"] = min(request_kwargs["max_tokens"], groq_max)
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
    primary = (global_settings.LLM_PROVIDER or "openai").strip().lower()
    provider_names = [primary]
    fallback_raw = getattr(global_settings, "LLM_FALLBACK_PROVIDERS", "") or ""
    for item in fallback_raw.split(","):
        prov = item.strip().lower()
        if prov and prov not in provider_names:
            provider_names.append(prov)

    specs: list[LLMProvider] = []
    for name in provider_names:
        api_key = ""
        model = ""
        base_url = None
        json_mode = False

        if name == "openrouter":
            api_key = global_settings.OPENROUTER_API_KEY
            model = global_settings.LLM_MODEL or global_settings.OPENROUTER_LLM_MODEL
            base_url = global_settings.OPENROUTER_BASE_URL
            json_mode = True
        elif name == "shopaikey":
            api_key = global_settings.OPENAI_API_KEY
            model = global_settings.LLM_MODEL
            base_url = "https://api.shopaikey.com/v1"
            json_mode = True
        elif name == "deepseek":
            api_key = global_settings.DEEPSEEK_API_KEY or global_settings.OPENAI_API_KEY
            model = global_settings.LLM_MODEL
            base_url = "https://api.deepseek.com/v1"
            json_mode = True
        elif name == "groq":
            api_key = global_settings.GROQ_API_KEY
            model = getattr(global_settings, "GROQ_MODEL", "") or getattr(global_settings, "GROQ_LLM_MODEL", "") or "llama-3.3-70b-versatile"
            base_url = "https://api.groq.com/openai/v1"
            json_mode = True
        elif name == "openai":
            api_key = global_settings.OPENAI_API_KEY
            model = global_settings.LLM_MODEL
            base_url = None
            json_mode = False

        if api_key:
            specs.append(
                LLMProvider(
                    name=name,
                    api_key=api_key,
                    model=model,
                    base_url=base_url,
                    json_mode=json_mode,
                )
            )

    return specs


def build_llm_client() -> FallbackLLMClient:
    providers = _provider_specs()
    if not providers:
        raise RuntimeError("No LLM provider API key configured")
    return FallbackLLMClient(providers)
