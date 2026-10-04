"""Verification of candidate pairs and clustering of verified pairs
(plan, Section 2.1 steps 6-8).

Clustering is transitive: if A~B and B~C, then A and C share a cluster even when
A and C are not similar. Each cluster therefore reports the minimum and average
similarity over its verified edges, so chain-shaped clusters are visible.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

import numpy as np

from .minhash import MinHasher
from .similarity import SimilarPair, jaccard
from .union_find import UnionFind


@dataclass
class Cluster:
    cluster_id: int
    members: list[int]  # element indices, ascending
    representative: int  # member with the most verified edges (ties: smallest index)
    min_sim: float
    avg_sim: float
    n_edges: int

    @property
    def size(self) -> int:
        return len(self.members)


class DuplicateClusterer:
    def __init__(self, threshold: float = 0.6, verify: str = "exact") -> None:
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("threshold must be in [0, 1]")
        if verify not in ("exact", "fast"):
            raise ValueError("verify must be 'exact' or 'fast'")
        self.threshold = threshold
        self.verify_mode = verify

    def verify(
        self,
        candidates: Iterable[tuple[int, int]],
        shingle_sets: Sequence[set] | None = None,
        signatures: np.ndarray | None = None,
    ) -> list[SimilarPair]:
        """Keep candidate pairs whose similarity reaches the threshold.

        exact: Jaccard on the shingle sets (needs shingle_sets).
        fast: MinHash estimate (needs signatures).
        """
        t = self.threshold
        out: list[SimilarPair] = []
        for a, b in sorted(candidates):
            if self.verify_mode == "exact":
                if shingle_sets is None:
                    raise ValueError("exact verification needs shingle_sets")
                sim = jaccard(shingle_sets[a], shingle_sets[b])
            else:
                if signatures is None:
                    raise ValueError("fast verification needs signatures")
                sim = MinHasher.estimate_jaccard(signatures[a], signatures[b])
            if sim >= t:
                out.append(SimilarPair(a, b, sim) if a < b else SimilarPair(b, a, sim))
        return out

    @staticmethod
    def cluster(n: int, edges: Iterable[SimilarPair]) -> list[Cluster]:
        """Connected components (size >= 2) of the graph on 0..n-1 given by edges.

        Clusters are ordered by size (largest first), then by smallest member.
        """
        edges = list(edges)
        uf = UnionFind(n)
        for e in edges:
            uf.union(e.a, e.b)

        sims: dict[int, list[float]] = {}
        degree = [0] * n
        for e in edges:
            sims.setdefault(uf.find(e.a), []).append(e.similarity)
            degree[e.a] += 1
            degree[e.b] += 1

        groups = [g for g in uf.components() if len(g) > 1]
        groups.sort(key=lambda g: (-len(g), g[0]))
        clusters = []
        for cid, members in enumerate(groups):
            s = sims[uf.find(members[0])]
            rep = max(members, key=lambda m: (degree[m], -m))
            clusters.append(Cluster(cid, members, rep, min(s), sum(s) / len(s), len(s)))
        return clusters
