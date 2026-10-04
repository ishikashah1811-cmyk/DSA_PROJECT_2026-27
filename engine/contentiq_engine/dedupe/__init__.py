"""Module 1: content similarity and duplicate detection."""

from .brute_force import BruteForceDetector
from .exact import ExactDuplicates, group_exact_duplicates
from .lsh import LSHIndex
from .minhash import MinHasher
from .similarity import SimilarPair, jaccard

__all__ = [
    "BruteForceDetector",
    "ExactDuplicates",
    "group_exact_duplicates",
    "LSHIndex",
    "MinHasher",
    "SimilarPair",
    "jaccard",
]
