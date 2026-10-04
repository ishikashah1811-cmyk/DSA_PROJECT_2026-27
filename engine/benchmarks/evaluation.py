"""Scoring helpers for the Module 1 benchmark (plan, Section 2.1.1).

Two kinds of ground truth:
- brute force: every pair with exact Jaccard >= t (same shingles); scores how much
  LSH loses compared with the exact method (recall, and precision in fast mode).
- planted labels: (original, edited copy) pairs from the data generator; scores the
  whole pipeline including the shingle choice (precision, recall, F1).
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from itertools import combinations

Pair = tuple[int, int]


def ordered(x: int, y: int) -> Pair:
    return (x, y) if x < y else (y, x)


def pair_scores(found: set[Pair], truth: set[Pair]) -> tuple[float, float]:
    """(precision, recall) of found against truth; an empty denominator scores 1.0."""
    hit = len(found & truth)
    precision = hit / len(found) if found else 1.0
    recall = hit / len(truth) if truth else 1.0
    return precision, recall


def expand_to_captions(
    doc_pairs: Iterable[Pair],
    doc_caption: list[int],
    members: dict[int, list[int]],
    exact_groups: Iterable[list[int]],
) -> set[Pair]:
    """Map pairs of compared documents back to caption-index pairs.

    Each compared document stands for every caption that was identical to it after
    normalization (exact-duplicate pre-pass), and those identical captions are
    pairs of their own.
    """
    out: set[Pair] = set()
    for a, b in doc_pairs:
        for x in members[doc_caption[a]]:
            for y in members[doc_caption[b]]:
                out.add(ordered(x, y))
    for group in exact_groups:
        out.update(ordered(x, y) for x, y in combinations(group, 2))
    return out


def connected_components(pairs: Iterable[Pair]) -> dict[int, int]:
    """Node -> component id, by breadth-first search over the pair graph."""
    adj: dict[int, list[int]] = defaultdict(list)
    for x, y in pairs:
        adj[x].append(y)
        adj[y].append(x)
    comp: dict[int, int] = {}
    for start in adj:
        if start in comp:
            continue
        comp[start] = start
        queue = [start]
        while queue:
            node = queue.pop()
            for nxt in adj[node]:
                if nxt not in comp:
                    comp[nxt] = start
                    queue.append(nxt)
    return comp


@dataclass
class LabelScores:
    tp: int
    fp: int
    fn: int
    ignored: int  # predicted pairs linked only through a chain of planted copies
    precision: float
    recall: float
    f1: float


def label_scores(predicted: set[Pair], planted: Iterable[Pair]) -> LabelScores:
    """Score predicted caption pairs against planted (original, copy) pairs.

    A copy of a copy is similar to the original but was not planted directly. Such
    pairs (same planted component, not a planted pair) are neither rewarded nor
    counted as false positives.
    """
    positives = {ordered(x, y) for x, y in planted if x != y}
    comp = connected_components(positives)
    tp = len(predicted & positives)
    ignored = sum(
        1 for x, y in predicted - positives if x in comp and y in comp and comp[x] == comp[y]
    )
    fp = len(predicted) - tp - ignored
    fn = len(positives) - tp
    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / len(positives) if positives else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return LabelScores(tp, fp, fn, ignored, precision, recall, f1)
