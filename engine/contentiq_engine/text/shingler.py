"""Caption -> set of shingles / 32-bit shingle IDs (plan, Section 2.1 step 3).

Shingle IDs use a stable hash (BLAKE2b truncated to 4 bytes), not Python's
built-in hash(), which is randomized per process for strings and would make
MinHash signatures irreproducible across runs.
"""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from collections.abc import Iterable

DEFAULT_MIN_SHINGLES = 10
# Character 4-grams had the best F1 against planted duplicates in the Module 1
# shingle x threshold sweep (docs/benchmarks/RESULTS.md); the plan started at 5.
DEFAULT_CHAR_K = 4
DEFAULT_WORD_K = 2


def stable_hash32(s: str) -> int:
    """Deterministic unsigned 32-bit hash of a string, identical in every process."""
    return int.from_bytes(hashlib.blake2b(s.encode("utf-8"), digest_size=4).digest(), "little")


class Shingler(ABC):
    """Common interface so character and word shingles are interchangeable."""

    k: int

    @abstractmethod
    def shingles(self, text: str) -> set[str]:
        """String shingles; used for exact Jaccard checks against the hashed IDs."""

    def shingle_ids(self, text: str) -> set[int]:
        return {stable_hash32(s) for s in self.shingles(text)}


class CharShingler(Shingler):
    """Character k-grams over the normalized text (spaces included)."""

    def __init__(self, k: int = DEFAULT_CHAR_K) -> None:
        if k < 1:
            raise ValueError("k must be >= 1")
        self.k = k

    def shingles(self, text: str) -> set[str]:
        if len(text) < self.k:
            return {text} if text else set()
        return {text[i : i + self.k] for i in range(len(text) - self.k + 1)}


class WordShingler(Shingler):
    """Word k-grams, words joined by a single space."""

    def __init__(self, k: int = DEFAULT_WORD_K) -> None:
        if k < 1:
            raise ValueError("k must be >= 1")
        self.k = k

    def shingles(self, text: str) -> set[str]:
        words = text.split()
        if len(words) < self.k:
            return {" ".join(words)} if words else set()
        return {" ".join(words[i : i + self.k]) for i in range(len(words) - self.k + 1)}


def make_shingler(kind: str = "char", k: int | None = None) -> Shingler:
    if kind == "char":
        return CharShingler(DEFAULT_CHAR_K if k is None else k)
    if kind == "word":
        return WordShingler(DEFAULT_WORD_K if k is None else k)
    raise ValueError(f"unknown shingle type {kind!r}; expected 'char' or 'word'")


def shingle_corpus(
    texts: Iterable[str], shingler: Shingler, min_shingles: int = DEFAULT_MIN_SHINGLES
) -> tuple[list[set[int]], list[int]]:
    """Shingle every text. Returns (shingle-ID sets, indices flagged as too short).

    Flagged captions have too few shingles for a reliable Jaccard estimate and
    should be reported instead of clustered.
    """
    sets: list[set[int]] = []
    flagged: list[int] = []
    for i, text in enumerate(texts):
        ids = shingler.shingle_ids(text)
        if len(ids) < min_shingles:
            flagged.append(i)
        sets.append(ids)
    return sets, flagged
