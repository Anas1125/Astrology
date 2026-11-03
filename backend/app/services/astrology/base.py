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
    pass
