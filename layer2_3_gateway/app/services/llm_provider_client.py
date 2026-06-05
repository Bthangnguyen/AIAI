# -*- coding: utf-8 -*-
"""OpenAI-compatible LLM client routing with provider fallback."""

import logging
from typing import Any, Optional, Type

import instructor
from openai import AsyncOpenAI
from pydantic import BaseModel

from app.config import settings as global_settings

logger = logging.getLogger(__name__)


class LLMProviderClient:
    """Creates Instructor clients and retries a request across configured providers."""

    _clients: dict[str, Any] = {}

    @classmethod
    def _normalize_provider(cls, provider: Optional[str]) -> str:
        return (provider or "openai").strip().lower()

    @classmethod
    def _provider_order(cls) -> list[str]:
        primary = cls._normalize_provider(global_settings.LLM_PROVIDER)
        providers = [primary]
        fallback_raw = getattr(global_settings, "LLM_FALLBACK_PROVIDERS", "") or ""
        for item in fallback_raw.split(","):
            provider = cls._normalize_provider(item)
            if provider and provider not in providers:
                providers.append(provider)
        return providers

    @classmethod
    def _api_key_for(cls, provider: str) -> str:
        if provider == "openrouter":
            return global_settings.OPENROUTER_API_KEY
        if provider == "shopaikey":
            return global_settings.OPENAI_API_KEY
        if provider == "groq":
            return global_settings.GROQ_API_KEY
        return global_settings.OPENAI_API_KEY

    @classmethod
    def _model_for(cls, provider: str) -> str:
        if provider == "groq":
            return global_settings.GROQ_MODEL
        return global_settings.LLM_MODEL

    @classmethod
    def _max_tokens_for(cls, provider: str, requested: Optional[int]) -> Optional[int]:
        if requested is None:
            return None
        if provider == "groq":
            return min(requested, global_settings.GROQ_MAX_TOKENS)
        return requested

    @classmethod
    def _base_url_for(cls, provider: str) -> Optional[str]:
        if provider == "openrouter":
            return "https://openrouter.ai/api/v1"
        if provider == "shopaikey":
            return "https://api.shopaikey.com/v1"
        if provider == "groq":
            return "https://api.groq.com/openai/v1"
        return None

    @classmethod
    def _client_for(cls, provider: str):
        if provider in cls._clients:
            return cls._clients[provider]

        api_key = cls._api_key_for(provider)
        if not api_key:
            raise RuntimeError(f"Missing API key for LLM provider '{provider}'")

        base_url = cls._base_url_for(provider)
        if base_url:
            base_client = AsyncOpenAI(base_url=base_url, api_key=api_key)
        else:
            base_client = AsyncOpenAI(api_key=api_key)

        if provider in {"shopaikey", "openrouter", "groq"}:
            client = instructor.from_openai(base_client, mode=instructor.Mode.JSON)
        else:
            client = instructor.from_openai(base_client)

        cls._clients[provider] = client
        return client

    @classmethod
    async def create_chat_completion(
        cls,
        *,
        response_model: Type[BaseModel],
        messages: list[dict[str, str]],
        operation_name: str,
        max_tokens: Optional[int] = None,
        max_retries: int = 2,
        timeout: float = 60.0,
    ) -> BaseModel:
        """Try the primary provider first, then configured fallback providers."""
        last_error: Optional[Exception] = None
        for provider in cls._provider_order():
            try:
                kwargs: dict[str, Any] = {
                    "model": cls._model_for(provider),
                    "response_model": response_model,
                    "messages": messages,
                    "max_retries": max_retries,
                    "timeout": timeout,
                }
                provider_max_tokens = cls._max_tokens_for(provider, max_tokens)
                if provider_max_tokens is not None:
                    kwargs["max_tokens"] = provider_max_tokens

                result = await cls._client_for(provider).chat.completions.create(**kwargs)
                if provider != cls._normalize_provider(global_settings.LLM_PROVIDER):
                    logger.warning(
                        "LLM %s succeeded via fallback provider '%s'",
                        operation_name,
                        provider,
                    )
                return result
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "LLM %s failed on provider '%s': %s",
                    operation_name,
                    provider,
                    exc,
                )

        assert last_error is not None
        raise last_error
