"""Exact Jaccard similarity and the pair type shared by the detectors."""

from __future__ import annotations

from collections.abc import Hashable
from typing import NamedTuple


class SimilarPair(NamedTuple):
    a: Hashable  # always the smaller id of the two
    b: Hashable
    similarity: float


def jaccard(x: set, y: set) -> float:
    """|x & y| / |x | y|. Two empty sets return 0.0 (no evidence of similarity)."""
    if not x and not y:
        return 0.0
    inter = len(x & y)
    return inter / (len(x) + len(y) - inter)
