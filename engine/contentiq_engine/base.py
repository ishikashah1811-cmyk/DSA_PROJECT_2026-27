"""Shared analyzer interface (Strategy pattern, plan Section 2.3)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from .models import Post


@dataclass
class AnalysisResult:
    module: str
    params: dict[str, Any] = field(default_factory=dict)
    data: dict[str, Any] = field(default_factory=dict)
    runtime_ms: float = 0.0


class AnalyzerModule(ABC):
    name: str

    @abstractmethod
    def ingest(self, posts: list[Post]) -> None: ...

    @abstractmethod
    def run(self, **params: Any) -> AnalysisResult: ...
