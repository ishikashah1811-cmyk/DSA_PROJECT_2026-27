"""HashtagRanker: per-tag engagement statistics and top-K ranking (plan, Section 2.2).

A plain average is noisy: a tag used once on a viral post would beat a tag used
40 times with a strong average. Tags below min_count are dropped and the rest are
ranked by a smoothed mean that pulls small samples toward the global mean:

    score = (sum_engagement + m * global_mean) / (count + m)

Engagement per post is likes + comments. Posts from accounts of different sizes are
not comparable, so when every post has a follower count it is normalized to
engagement per 1,000 followers.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from ..models import Post
from .max_heap import MaxHeap


@dataclass
class TagStats:
    tag: str
    count: int
    mean_engagement: float
    score: float


class _Desc:
    """Wraps a string so that a max-heap prefers alphabetically smaller tags on ties."""

    __slots__ = ("s",)

    def __init__(self, s: str) -> None:
        self.s = s

    def __lt__(self, other: _Desc) -> bool:
        return self.s > other.s

    def __gt__(self, other: _Desc) -> bool:
        return self.s < other.s

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _Desc) and self.s == other.s

    def __ge__(self, other: _Desc) -> bool:
        return self.s <= other.s

    def __le__(self, other: _Desc) -> bool:
        return self.s >= other.s


class HashtagRanker:
    def __init__(self, normalize: str = "auto") -> None:
        if normalize not in ("auto", "followers", "none"):
            raise ValueError("normalize must be 'auto', 'followers' or 'none'")
        self.normalize = normalize
        self._count: dict[str, int] = {}  # Python's dict is the hash table: O(1) amortized updates
        self._sum: dict[str, float] = {}
        self._n_posts = 0
        self._total = 0.0
        self.normalized = False

    @staticmethod
    def engagement(post: Post, per_followers: bool) -> float:
        raw = post.likes + post.comments
        if per_followers:
            return 1000.0 * raw / post.followers if post.followers else 0.0
        return float(raw)

    def ingest(self, posts: Iterable[Post]) -> None:
        posts = list(posts)
        if self.normalize == "auto":
            self.normalized = bool(posts) and all(p.followers for p in posts)
        else:
            self.normalized = self.normalize == "followers"
        self._count.clear()
        self._sum.clear()
        self._n_posts = len(posts)
        self._total = 0.0
        for post in posts:
            e = self.engagement(post, self.normalized)
            self._total += e
            for tag in set(post.hashtags):  # a tag repeated in one caption counts once
                self._count[tag] = self._count.get(tag, 0) + 1
                self._sum[tag] = self._sum.get(tag, 0.0) + e

    @property
    def global_mean(self) -> float:
        return self._total / self._n_posts if self._n_posts else 0.0

    def stats(self, m: float = 5.0, min_count: int = 3) -> list[TagStats]:
        """Stats for every tag used at least min_count times (unsorted)."""
        g = self.global_mean
        return [
            TagStats(tag, c, self._sum[tag] / c, (self._sum[tag] + m * g) / (c + m))
            for tag, c in self._count.items()
            if c >= min_count
        ]

    def top_k(self, k: int = 10, m: float = 5.0, min_count: int = 3) -> list[TagStats]:
        """Highest-scoring tags: heapify all eligible tags in O(n), then k pops in O(k log n).

        Ties on score go to the more used tag, then alphabetical order.
        """
        heap = MaxHeap(((s.score, s.count, _Desc(s.tag)), s) for s in self.stats(m, min_count))
        return [value for _, value in heap.top_k(k)]
