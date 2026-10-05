"""AnalyticsService: the facade the API talks to (plan, Section 2.3).

It registers AnalyzerModule implementations, gives them all the same posts, runs
them by name and exposes Module 2's interactive autocomplete.
"""

from __future__ import annotations

from typing import Any

from .base import AnalysisResult, AnalyzerModule
from .dedupe import DuplicateAnalyzer
from .hashtags import HashtagAnalyzer
from .models import Post


class AnalyticsService:
    def __init__(self, analyzers: list[AnalyzerModule] | None = None) -> None:
        self._analyzers: dict[str, AnalyzerModule] = {}
        self._posts: list[Post] = []
        for analyzer in analyzers or []:
            self.register(analyzer)

    @classmethod
    def default(cls) -> AnalyticsService:
        """Both ContentIQ modules: 'duplicates' (Module 1) and 'hashtags' (Module 2)."""
        return cls([DuplicateAnalyzer(), HashtagAnalyzer()])

    def register(self, analyzer: AnalyzerModule) -> None:
        if analyzer.name in self._analyzers:
            raise ValueError(f"an analyzer named {analyzer.name!r} is already registered")
        self._analyzers[analyzer.name] = analyzer
        if self._posts:
            analyzer.ingest(self._posts)

    @property
    def names(self) -> list[str]:
        return list(self._analyzers)

    @property
    def posts(self) -> list[Post]:
        return list(self._posts)

    def analyzer(self, name: str) -> AnalyzerModule:
        try:
            return self._analyzers[name]
        except KeyError:
            raise KeyError(f"no analyzer named {name!r}; registered: {self.names}") from None

    def ingest(self, posts: list[Post]) -> None:
        """Replace the post set in every analyzer."""
        self._posts = list(posts)
        for analyzer in self._analyzers.values():
            analyzer.ingest(self._posts)

    def run(self, name: str, **params: Any) -> AnalysisResult:
        return self.analyzer(name).run(**params)

    def run_all(self) -> dict[str, AnalysisResult]:
        """Every analyzer with its default parameters."""
        return {name: analyzer.run() for name, analyzer in self._analyzers.items()}

    def suggest(self, prefix: str, k: int = 10) -> list[tuple[str, int]]:
        analyzer = self.analyzer(HashtagAnalyzer.name)
        assert isinstance(analyzer, HashtagAnalyzer)
        return analyzer.suggest(prefix, k)
