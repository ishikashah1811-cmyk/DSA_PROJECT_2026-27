"""HashtagAnalyzer: Module 2 as an AnalyzerModule, plus interactive autocomplete
(plan, Sections 2.2 and 2.3)."""

from __future__ import annotations

import time
from typing import Any

from ..base import AnalysisResult, AnalyzerModule
from ..models import Post
from .ranker import HashtagRanker
from .trie import DEFAULT_CACHE_K, HashtagTrie

DEFAULT_PARAMS: dict[str, Any] = {"k": 10, "m": 5.0, "min_count": 3}


class HashtagAnalyzer(AnalyzerModule):
    name = "hashtags"

    def __init__(self, normalize: str = "auto", cache_k: int = DEFAULT_CACHE_K) -> None:
        self.normalize = normalize
        self.cache_k = cache_k
        self.trie = HashtagTrie(cache_k)
        self.ranker = HashtagRanker(normalize)

    def ingest(self, posts: list[Post]) -> None:
        self.trie = HashtagTrie(self.cache_k)
        for post in posts:
            for tag in set(post.hashtags):  # count posts using the tag, as the ranker does
                self.trie.insert(tag)
        self.trie.rebuild_cache()
        self.ranker = HashtagRanker(self.normalize)
        self.ranker.ingest(posts)

    def run(self, **params: Any) -> AnalysisResult:
        unknown = set(params) - set(DEFAULT_PARAMS)
        if unknown:
            raise ValueError(f"unknown parameters: {sorted(unknown)}")
        p = {**DEFAULT_PARAMS, **params}
        t0 = time.perf_counter()
        top = self.ranker.top_k(p["k"], p["m"], p["min_count"])
        data = {
            "n_tags": len(self.trie),
            "global_mean": round(self.ranker.global_mean, 4),
            "engagement_unit": "per_1000_followers" if self.ranker.normalized else "likes_plus_comments",
            "top": [
                {"tag": s.tag, "count": s.count, "mean_engagement": round(s.mean_engagement, 4),
                 "score": round(s.score, 4)}
                for s in top
            ],
        }
        return AnalysisResult(self.name, p, data, round((time.perf_counter() - t0) * 1000, 1))

    def suggest(self, prefix: str, k: int = 10) -> list[tuple[str, int]]:
        """Autocomplete: up to k most used tags starting with prefix ('#' and case ignored)."""
        return self.trie.suggest(prefix.lstrip("#").lower(), k)
