import pytest

from app.services.llm_client import FallbackLLMClient, LLMProvider


class _FakeCompletions:
    def __init__(self, result=None, exc=None):
        self.result = result
        self.exc = exc
        self.calls = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.exc:
            raise self.exc
        return self.result


class _FakeChat:
    def __init__(self, completions):
        self.completions = completions


class _FakeClient:
    def __init__(self, completions):
        self.chat = _FakeChat(completions)


@pytest.mark.anyio
async def test_fallback_llm_client_tries_openrouter_after_primary_failure(monkeypatch):
    primary = LLMProvider("shopaikey", "shop-key", "deepseek-chat", "https://shop", True)
    fallback = LLMProvider("openrouter", "or-key", "deepseek/deepseek-v4-flash", "https://or", True)
    client = FallbackLLMClient([primary, fallback])
    primary_completions = _FakeCompletions(exc=RuntimeError("quota exceeded"))
    fallback_completions = _FakeCompletions(result={"ok": True})

    def fake_client_for(provider):
        if provider.name == "shopaikey":
            return _FakeClient(primary_completions)
        return _FakeClient(fallback_completions)

    monkeypatch.setattr(client.chat.completions, "_client_for", fake_client_for)

    result = await client.chat.completions.create(model="ignored", messages=[])

    assert result == {"ok": True}
    assert primary_completions.calls[0]["model"] == "deepseek-chat"
    assert fallback_completions.calls[0]["model"] == "deepseek/deepseek-v4-flash"


@pytest.mark.anyio
async def test_fallback_llm_client_can_continue_to_groq(monkeypatch):
    shopaikey = LLMProvider("shopaikey", "shop-key", "deepseek-chat", "https://shop", True)
    openrouter = LLMProvider("openrouter", "or-key", "deepseek/deepseek-v4-flash", "https://or", True)
    groq = LLMProvider("groq", "groq-key", "llama-3.3-70b-versatile", "https://groq", True)
    client = FallbackLLMClient([shopaikey, openrouter, groq])
    shop_completions = _FakeCompletions(exc=RuntimeError("quota exceeded"))
    openrouter_completions = _FakeCompletions(exc=RuntimeError("upstream unavailable"))
    groq_completions = _FakeCompletions(result={"ok": True})

    def fake_client_for(provider):
        if provider.name == "shopaikey":
            return _FakeClient(shop_completions)
        if provider.name == "openrouter":
            return _FakeClient(openrouter_completions)
        return _FakeClient(groq_completions)

    monkeypatch.setattr(client.chat.completions, "_client_for", fake_client_for)

    result = await client.chat.completions.create(model="ignored", messages=[])

    assert result == {"ok": True}
    assert shop_completions.calls[0]["model"] == "deepseek-chat"
    assert openrouter_completions.calls[0]["model"] == "deepseek/deepseek-v4-flash"
    assert groq_completions.calls[0]["model"] == "llama-3.3-70b-versatile"
