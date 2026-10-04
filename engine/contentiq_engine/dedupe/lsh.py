"""Locality-Sensitive Hashing by banding (plan, Section 2.1 step 5).

The signature is split into b bands of r rows (b * r = h). Two documents become a
candidate pair if their signatures agree exactly on every row of at least one band.
For true similarity s: P(candidate) = 1 - (1 - s^r)^b, steepest near (1/b)^(1/r).
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Hashable, Iterable, Sequence
from dataclasses import dataclass
from itertools import combinations

import numpy as np


@dataclass
class LSHStats:
    n_docs: int
    n_buckets: int
    largest_bucket: int
    skipped_buckets: int  # buckets over max_bucket_size, ignored for candidates
    n_candidates: int


class LSHIndex:
    def __init__(self, bands: int = 32, rows: int = 4, max_bucket_size: int | None = None) -> None:
        if bands < 1 or rows < 1:
            raise ValueError("bands and rows must be >= 1")
        self.bands = bands
        self.rows = rows
        self.max_bucket_size = max_bucket_size
        # One hash table per band: band key (bytes of the r rows) -> doc ids.
        self._buckets: list[defaultdict[bytes, list[Hashable]]] = [defaultdict(list) for _ in range(bands)]
        self._n_docs = 0
        self._last_stats: LSHStats | None = None

    @property
    def num_hashes(self) -> int:
        return self.bands * self.rows

    def _band_keys(self, signature: Sequence[int] | np.ndarray) -> list[bytes]:
        sig = np.asarray(signature, dtype=np.uint64)
        if sig.shape != (self.num_hashes,):
            raise ValueError(f"signature length {sig.shape} does not match bands*rows = {self.num_hashes}")
        r = self.rows
        return [sig[i * r : (i + 1) * r].tobytes() for i in range(self.bands)]

    def add(self, doc_id: Hashable, signature: Sequence[int] | np.ndarray) -> None:
        for band, key in enumerate(self._band_keys(signature)):
            self._buckets[band][key].append(doc_id)
        self._n_docs += 1

    def add_many(self, doc_ids: Iterable[Hashable], signatures: np.ndarray) -> None:
        for doc_id, sig in zip(doc_ids, signatures):
            self.add(doc_id, sig)

    def query(self, signature: Sequence[int] | np.ndarray) -> set[Hashable]:
        """Ids sharing at least one band with the given signature."""
        found: set[Hashable] = set()
        for band, key in enumerate(self._band_keys(signature)):
            found.update(self._buckets[band].get(key, ()))
        return found

    def candidate_pairs(self) -> set[tuple[Hashable, Hashable]]:
        """All (smaller id, larger id) pairs that share a bucket in some band."""
        pairs: set[tuple[Hashable, Hashable]] = set()
        n_buckets = largest = skipped = 0
        for table in self._buckets:
            for members in table.values():
                n_buckets += 1
                size = len(members)
                largest = max(largest, size)
                if size < 2:
                    continue
                if self.max_bucket_size is not None and size > self.max_bucket_size:
                    skipped += 1
                    continue
                for x, y in combinations(members, 2):
                    pairs.add((x, y) if x < y else (y, x))
        self._last_stats = LSHStats(self._n_docs, n_buckets, largest, skipped, len(pairs))
        return pairs

    @property
    def stats(self) -> LSHStats | None:
        """Stats from the most recent candidate_pairs() call."""
        return self._last_stats

    @staticmethod
    def candidate_probability(s: float, bands: int, rows: int) -> float:
        return 1.0 - (1.0 - s**rows) ** bands

    @staticmethod
    def steep_point(bands: int, rows: int) -> float:
        return (1.0 / bands) ** (1.0 / rows)
