"""MinHash signatures (plan, Section 2.1 step 4).

h hash functions of the form (a*x + b) mod p with p = 2^32 - 5, the largest prime
below 2^32. Shingle IDs x are 32-bit and a, b < p, so a*x + b < 2^64 and every
step fits in numpy uint64 without overflow. The fraction of matching positions
between two signatures estimates Jaccard similarity with standard error about
sqrt(J(1-J)/h).
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

import numpy as np

PRIME = (1 << 32) - 5  # 4294967291
EMPTY_VALUE = PRIME  # larger than any hash value; fills the signature of an empty set

_P = np.uint64(PRIME)


class MinHasher:
    def __init__(self, num_hashes: int = 128, seed: int = 42) -> None:
        if num_hashes < 1:
            raise ValueError("num_hashes must be >= 1")
        self.num_hashes = num_hashes
        self.seed = seed
        rng = np.random.default_rng(seed)
        self.a = rng.integers(1, PRIME, size=num_hashes, dtype=np.uint64)
        self.b = rng.integers(0, PRIME, size=num_hashes, dtype=np.uint64)

    def signature(self, shingle_ids: Iterable[int]) -> np.ndarray:
        """Vectorized signature: uint64 array of length num_hashes."""
        ids = np.fromiter(shingle_ids, dtype=np.uint64)
        if ids.size == 0:
            return np.full(self.num_hashes, EMPTY_VALUE, dtype=np.uint64)
        hashed = (self.a[:, None] * ids[None, :] + self.b[:, None]) % _P
        return hashed.min(axis=1)

    def signature_python(self, shingle_ids: Iterable[int]) -> list[int]:
        """Plain-Python reference implementation; must equal signature()."""
        ids = list(shingle_ids)
        sig = []
        for a, b in zip(self.a.tolist(), self.b.tolist()):
            sig.append(min(((a * x + b) % PRIME for x in ids), default=EMPTY_VALUE))
        return sig

    def signatures(self, shingle_sets: Sequence[Iterable[int]]) -> np.ndarray:
        """Signature matrix of shape (n, num_hashes)."""
        out = np.empty((len(shingle_sets), self.num_hashes), dtype=np.uint64)
        for i, ids in enumerate(shingle_sets):
            out[i] = self.signature(ids)
        return out

    @staticmethod
    def estimate_jaccard(sig1: np.ndarray, sig2: np.ndarray) -> float:
        return float(np.mean(np.asarray(sig1) == np.asarray(sig2)))
