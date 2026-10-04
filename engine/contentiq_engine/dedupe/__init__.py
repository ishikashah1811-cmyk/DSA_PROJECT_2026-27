"""Module 1: content similarity and duplicate detection."""

from .analyzer import DuplicateAnalyzer
from .brute_force import BruteForceDetector
from .clusterer import Cluster, DuplicateClusterer
from .exact import ExactDuplicates, group_exact_duplicates
from .lsh import LSHIndex
from .minhash import MinHasher
from .similarity import SimilarPair, jaccard
from .union_find import UnionFind

__all__ = [
    "BruteForceDetector",
    "Cluster",
    "DuplicateAnalyzer",
    "DuplicateClusterer",
    "ExactDuplicates",
    "group_exact_duplicates",
    "LSHIndex",
    "MinHasher",
    "SimilarPair",
    "jaccard",
    "UnionFind",
]
