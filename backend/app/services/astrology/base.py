from abc import ABC, abstractmethod
from typing import Any


class AstrologyEngine(ABC):
    """Replaceable adapter boundary; implementations must not invent missing calculations."""

    @abstractmethod
    def calculate_chart(self, birth_data: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def calculate_planetary_positions(self, birth_data: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def calculate_houses(self, birth_data: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def calculate_transits(self, birth_data: dict[str, Any], at_time: str, config: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def calculate_compatibility(self, first: dict[str, Any], second: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


class EngineUnavailable(RuntimeError):
    """A calculation was refused, with a safe diagnostic category for logs."""

    def __init__(self, message: str, *, reason_code: str = "runtime_unavailable"):
        super().__init__(message)
        self.reason_code = reason_code


def ephemeris_failure_code(message: str) -> str:
    """Categorize native errors without copying paths or personal input into logs."""
    text = message.casefold()
    if "ephemeris" in text and any(marker in text for marker in ("file", "data", "coverage")):
        return "ephemeris_data_unavailable"
    return "native_runtime_unavailable"
