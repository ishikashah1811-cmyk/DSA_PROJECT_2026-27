"""Exact all-pairs baseline and ground truth (plan, Sections 2.1 and 2.1.1).

find_pairs: pure Python, n(n-1)/2 exact Jaccard comparisons, each O(s).
find_pairs_signatures: numpy-vectorized all-pairs comparison of MinHash signatures,
so LSH can also be timed against a baseline given the same tooling.
"""

from __future__ import annotations

from collections.abc import Hashable, Sequence

import numpy as np

from .similarity import SimilarPair, jaccard


class BruteForceDetector:
    def __init__(self, threshold: float = 0.6) -> None:
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("threshold must be in [0, 1]")
        self.threshold = threshold

    def find_pairs(self, shingle_sets: Sequence[set], ids: Sequence[Hashable] | None = None) -> list[SimilarPair]:
        """Every pair with exact Jaccard >= threshold."""
        ids = list(range(len(shingle_sets))) if ids is None else list(ids)
        t = self.threshold
        out: list[SimilarPair] = []
        n = len(shingle_sets)
        for i in range(n):
            si = shingle_sets[i]
            for j in range(i + 1, n):
                sim = jaccard(si, shingle_sets[j])
                if sim >= t:
                    out.append(_pair(ids[i], ids[j], sim))
        return out

    def find_pairs_signatures(
        self, signatures: np.ndarray, ids: Sequence[Hashable] | None = None
    ) -> list[SimilarPair]:
        """Every pair whose MinHash estimate >= threshold (one vectorized row at a time)."""
        n, h = signatures.shape
        ids = list(range(n)) if ids is None else list(ids)
        t = self.threshold
        out: list[SimilarPair] = []
        for i in range(n - 1):
            sims = (signatures[i + 1 :] == signatures[i]).sum(axis=1) / h
            for off in np.nonzero(sims >= t)[0]:
                j = i + 1 + int(off)
                out.append(_pair(ids[i], ids[j], float(sims[off])))
        return out


def _pair(x: Hashable, y: Hashable, sim: float) -> SimilarPair:
    return SimilarPair(x, y, sim) if x < y else SimilarPair(y, x, sim)
