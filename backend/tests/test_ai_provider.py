import asyncio

import httpx
import pytest

from app.core.config import settings
from app.services.ai.provider import (
    AIConfig,
    AIProviderTimeout,
    AIProviderUnavailable,
    OpenAICompatibleProvider,
    get_ai_provider,
)
from app.services.ai.context import build_chart_context


def test_provider_configuration_requires_credentials_and_supported_provider(monkeypatch):
    monkeypatch.setattr(settings, "ai_provider", "openai-compatible")
    monkeypatch.setattr(settings, "ai_base_url", None)
    monkeypatch.setattr(settings, "ai_api_key", None)
    monkeypatch.setattr(settings, "ai_model", None)
    with pytest.raises(AIProviderUnavailable, match="not configured"):
        get_ai_provider()
    monkeypatch.setattr(settings, "ai_provider", "unknown")
    with pytest.raises(AIProviderUnavailable, match="not supported"):
        get_ai_provider()
    monkeypatch.setattr(settings, "ai_provider", "openai-compatible")
    monkeypatch.setattr(settings, "ai_base_url", "http://provider.example/v1")
    monkeypatch.setattr(settings, "ai_api_key", "configured-but-never-printed")
    monkeypatch.setattr(settings, "ai_model", "test-model")
    with pytest.raises(AIProviderUnavailable, match="HTTPS"):
        get_ai_provider()


def test_western_context_contains_only_saved_houses_and_aspects():
    profile = {"id": "profile-1", "display_name": "Private", "birth_date": "1990-01-01", "birthplace": "Private place"}
    calculation = {
        "status": "complete", "calculation_system": "western", "profile_id": "profile-1", "division": "W",
        "input_snapshot": {"birth_date": "1990-01-01", "birthplace": "Private place"},
        "result": {
            "calculation_system": "western",
            "planets": [{"name": "Moon", "longitude": 44.2, "sign": "Taurus", "house": 2, "retrograde": False}],
            "houses": [{"number": 2, "cusp_longitude": 33, "sign": "Taurus"}],
            "aspects": [{"planet_a": "Sun", "planet_b": "Moon", "aspect": "trine", "orb": 1.2, "motion": "applying"}],
            "midheaven": {"longitude": 270.0, "sign": "Capricorn"},
        },
    }
    context = build_chart_context(profile, calculation, "western")
    assert context["available"] is True
    assert context["planets"][0]["name"] == "Moon"
    assert context["houses"][0]["number"] == 2
    assert context["aspects"][0]["motion"] == "applying"
    assert "birthplace" not in str(context) and "birth_date" not in str(context)

def test_openai_compatible_provider_parses_sse_and_usage(monkeypatch):
    requests = []

    class Response:
        is_error = False
        status_code = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return None

        async def aiter_lines(self):
            for line in [
                'data: {"choices":[{"delta":{"content":"Hello "}}]}',
                'data: {"choices":[{"delta":{"content":"வணக்கம்"}}]}',
                'data: {"choices":[],"usage":{"prompt_tokens":7,"completion_tokens":3}}',
                "data: [DONE]",
            ]:
                yield line

    class Client:
        def __init__(self, timeout):
            assert timeout == 12

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return None

        def stream(self, method, url, **kwargs):
            requests.append((method, url, kwargs))
            return Response()

    monkeypatch.setattr(httpx, "AsyncClient", Client)
    adapter = OpenAICompatibleProvider(AIConfig("https://provider.test/v1", "secret", "model-x", timeout_seconds=12))
    chunks = asyncio.run(_collect(adapter.stream([{"role": "user", "content": "hi"}])))
    assert [chunk.content for chunk in chunks] == ["Hello ", "வணக்கம்", ""]
    assert (chunks[-1].input_tokens, chunks[-1].output_tokens) == (7, 3)
    method, url, kwargs = requests[0]
    assert (method, url) == ("POST", "https://provider.test/v1/chat/completions")
    assert kwargs["headers"]["Authorization"] == "Bearer secret"
    assert kwargs["json"]["stream"] is True
    assert kwargs["json"]["stream_options"]["include_usage"] is True


async def _collect(iterator):
    return [chunk async for chunk in iterator]


def test_openai_compatible_provider_maps_timeout_without_leaking_details(monkeypatch):
    class Client:
        def __init__(self, timeout):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return None

        def stream(self, *_args, **_kwargs):
            raise httpx.ReadTimeout("provider request carried secret data")

    monkeypatch.setattr(httpx, "AsyncClient", Client)
    adapter = OpenAICompatibleProvider(AIConfig("https://provider.test/v1", "secret", "model-x"))

    async def run():
        with pytest.raises(AIProviderTimeout) as error:
            await _collect(adapter.stream([]))
        assert "secret data" not in str(error.value)

    asyncio.run(run())


def test_openai_compatible_provider_sanitizes_provider_http_failure(monkeypatch):
    class Response:
        is_error = True
        status_code = 429

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return None

    class Client:
        def __init__(self, timeout):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return None

        def stream(self, *_args, **_kwargs):
            return Response()

    monkeypatch.setattr(httpx, "AsyncClient", Client)
    adapter = OpenAICompatibleProvider(AIConfig("https://provider.test/v1", "secret", "model-x"))

    async def run():
        with pytest.raises(AIProviderUnavailable, match="HTTP 429"):
            await _collect(adapter.stream([]))

    asyncio.run(run())


@pytest.mark.parametrize(
    "lines",
    [
        ['data: {"choices":[{"delta":{"content":"partial text"}}]}'],
        ['data: {"error":{"message":"private upstream details"}}', "data: [DONE]"],
    ],
)
def test_openai_compatible_provider_rejects_incomplete_or_error_streams(monkeypatch, lines):
    class Response:
        is_error = False
        status_code = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return None

        async def aiter_lines(self):
            for line in lines:
                yield line

    class Client:
        def __init__(self, timeout):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return None

        def stream(self, *_args, **_kwargs):
            return Response()

    monkeypatch.setattr(httpx, "AsyncClient", Client)
    adapter = OpenAICompatibleProvider(AIConfig("https://provider.test/v1", "secret", "model-x"))

    async def run():
        with pytest.raises(AIProviderUnavailable) as error:
            await _collect(adapter.stream([]))
        assert "private upstream details" not in str(error.value)

    asyncio.run(run())
