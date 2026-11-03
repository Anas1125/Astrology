"""Provider-neutral interface and an OpenAI-compatible asynchronous SSE adapter."""
from collections.abc import AsyncIterator, Mapping, Sequence
from dataclasses import dataclass
import json
from typing import Protocol
from urllib.parse import urlparse

from app.core.config import settings


@dataclass(frozen=True)
class AIConfig:
    base_url: str
    api_key: str
    model: str
    timeout_seconds: float = 30.0
    temperature: float = 0.6
    max_tokens: int = 1200


@dataclass(frozen=True)
class AIStreamChunk:
    content: str = ""
    input_tokens: int | None = None
    output_tokens: int | None = None


class AIProvider(Protocol):
    async def stream(self, messages: Sequence[Mapping[str, str]]) -> AsyncIterator[AIStreamChunk]: ...


class AIProviderUnavailable(RuntimeError):
    """The provider is not configured or is temporarily inaccessible."""


class AIProviderTimeout(AIProviderUnavailable):
    pass


class OpenAICompatibleProvider:
    """Adapter for `/chat/completions` providers that implement OpenAI's SSE format."""

    def __init__(self, config: AIConfig):
        self.config = config

    async def stream(self, messages: Sequence[Mapping[str, str]]) -> AsyncIterator[AIStreamChunk]:
        try:
            import httpx
        except ImportError as exc:
            raise AIProviderUnavailable("Install the backend `ai` extra to enable the configured provider") from exc

        url = self.config.base_url.rstrip("/") + "/chat/completions"
        payload = {
            "model": self.config.model,
            "messages": list(messages),
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        try:
            completed = False
            async with httpx.AsyncClient(timeout=self.config.timeout_seconds) as client:
                async with client.stream(
                    "POST", url,
                    headers={"Authorization": f"Bearer {self.config.api_key}"},
                    json=payload,
                ) as response:
                    if response.is_error:
                        raise AIProviderUnavailable(f"AI provider returned HTTP {response.status_code}")
                    async for line in response.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        raw = line[5:].strip()
                        if not raw or raw == "[DONE]":
                            if raw == "[DONE]":
                                completed = True
                                break
                            continue
                        try:
                            event = json.loads(raw)
                        except json.JSONDecodeError:
                            continue
                        if event.get("error") is not None:
                            raise AIProviderUnavailable("The AI provider rejected the streaming request")
                        usage = event.get("usage") or {}
                        choices = event.get("choices") or []
                        content = ""
                        if choices:
                            delta = choices[0].get("delta") or {}
                            value = delta.get("content")
                            if isinstance(value, str):
                                content = value
                        input_tokens = usage.get("prompt_tokens")
                        output_tokens = usage.get("completion_tokens")
                        if content or input_tokens is not None or output_tokens is not None:
                            yield AIStreamChunk(
                                content=content,
                                input_tokens=input_tokens if isinstance(input_tokens, int) else None,
                                output_tokens=output_tokens if isinstance(output_tokens, int) else None,
                            )
            if not completed:
                raise AIProviderUnavailable("The AI provider stream ended before completion")
        except httpx.TimeoutException as exc:
            raise AIProviderTimeout("The AI provider timed out. Please try again.") from exc
        except httpx.HTTPError as exc:
            raise AIProviderUnavailable("The AI provider could not be reached. Please try again.") from exc


def get_ai_provider() -> AIProvider:
    provider_name = settings.ai_provider.strip().lower()
    if provider_name not in {"openai-compatible", "openai_compatible"}:
        raise AIProviderUnavailable("The configured AI provider is not supported")
    base_url = (settings.ai_base_url or "").strip().rstrip("/")
    api_key = (settings.ai_api_key or "").strip()
    model = (settings.ai_model or "").strip()
    if not base_url or not api_key or not model:
        raise AIProviderUnavailable("AI astrologer is unavailable because its provider is not configured")
    parsed_url = urlparse(base_url)
    is_local_http = parsed_url.scheme == "http" and parsed_url.hostname in {"localhost", "127.0.0.1", "::1"}
    if parsed_url.scheme != "https" and not is_local_http or not parsed_url.hostname or parsed_url.username or parsed_url.password:
        raise AIProviderUnavailable("AI provider base URL must use HTTPS outside local development")
    if settings.ai_timeout_seconds <= 0:
        raise AIProviderUnavailable("AI provider timeout must be greater than zero")
    return OpenAICompatibleProvider(AIConfig(
        base_url=base_url,
        api_key=api_key,
        model=model,
        timeout_seconds=settings.ai_timeout_seconds,
        max_tokens=settings.ai_max_tokens,
    ))
