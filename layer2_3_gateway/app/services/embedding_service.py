"""Shared embedding service for both Gateway (async) and Ingestion (sync).

Provides both sync and async methods:
- embed_text() / embed_batch() — for batch ingestion scripts
- aembed_text() — for non-blocking use inside FastAPI event loop
"""

import os
from typing import List, Optional
from openai import OpenAI, AsyncOpenAI

EMBEDDING_MODEL = "text-embedding-3-small"  # 1536 dimensions
EMBEDDING_DIM = 1536


class EmbeddingService:
    """Generates vector embeddings for POI text."""

    def __init__(self, api_key: Optional[str] = None):
        provider = os.getenv("LLM_PROVIDER", "openai")
        if provider == "openrouter":
            self._api_key = api_key or os.getenv("OPENROUTER_API_KEY", "")
            self._base_url = "https://openrouter.ai/api/v1"
            self._model = "openai/text-embedding-3-small"
        elif provider == "shopaikey":
            self._api_key = api_key or os.getenv("OPENAI_API_KEY", "")
            self._base_url = "https://api.shopaikey.com/v1"
            self._model = "text-embedding-3-small"
        else:
            self._api_key = api_key or os.getenv("OPENAI_API_KEY", "")
            self._base_url = None
            self._model = "text-embedding-3-small"

        self._sync_client = None
        self._async_client = None

    @property
    def sync_client(self) -> OpenAI:
        """Lazy-init sync client (for ingestion scripts)."""
        if self._sync_client is None:
            self._sync_client = OpenAI(api_key=self._api_key, base_url=self._base_url)
        return self._sync_client

    @property
    def async_client(self) -> AsyncOpenAI:
        """Lazy-init async client (for FastAPI Gateway)."""
        if self._async_client is None:
            self._async_client = AsyncOpenAI(api_key=self._api_key, base_url=self._base_url)
        return self._async_client

    # --- Sync methods (Ingestion) ---

    def embed_text(self, text: str) -> List[float]:
        """Convert a single text string to 1536-dim vector (sync)."""
        response = self.sync_client.embeddings.create(
            model=self._model, input=text,
        )
        return response.data[0].embedding

    def embed_batch(self, texts: List[str], batch_size: int = 100) -> List[List[float]]:
        """Batch embed multiple texts (sync). OpenAI supports up to 2048 inputs."""
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            response = self.sync_client.embeddings.create(
                model=self._model, input=batch,
            )
            all_embeddings.extend([d.embedding for d in response.data])
        return all_embeddings

    # --- Async methods (Gateway) ---

    async def aembed_text(self, text: str) -> List[float]:
        """Convert text to vector (async, non-blocking for FastAPI)."""
        response = await self.async_client.embeddings.create(
            model=self._model, input=text,
        )
        return response.data[0].embedding

    # --- Utilities ---

    @staticmethod
    def build_poi_text(name: str, category: str, tags: List[str], description: str = "") -> str:
        """Combine POI fields into a single embedding-ready text.

        Example output:
            "Đại Nội Huế | historical, culture | UNESCO World Heritage imperial citadel"
        """
        tag_str = ", ".join(tags) if tags else ""
        parts = [name, category]
        if tag_str:
            parts.append(tag_str)
        if description:
            parts.append(description)
        return " | ".join(parts)

    @staticmethod
    def build_distribution_query_text(
        distribution_description: str,
        tags: List[str],
        destination: str = "Huế",
    ) -> str:
        """Build rich query text from LLM distribution description for semantic search.

        Example output:
            "Du lịch Huế. Ẩm thực đường phố: bún bò, bánh khoái, cơm hến, chè Huế."
        """
        parts = [f"Du lịch {destination}"]
        if distribution_description:
            parts.append(distribution_description)
        if tags:
            parts.append(", ".join(tags))
        return ". ".join(parts)
