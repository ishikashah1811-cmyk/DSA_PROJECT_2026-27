"""Exact-duplicate pre-pass (plan, Section 2.1 step 2).

Identical normalized captions are grouped immediately and only one representative
enters LSH, so templated captions do not pile into one bucket.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass
class ExactDuplicates:
    representatives: list[int]  # index of the first occurrence of each distinct text
    groups: list[list[int]]  # indices sharing one text; only groups of size >= 2


def group_exact_duplicates(normalized_texts: Sequence[str]) -> ExactDuplicates:
    first_seen: dict[str, int] = {}
    members: dict[int, list[int]] = {}
    for i, text in enumerate(normalized_texts):
        rep = first_seen.setdefault(text, i)
        members.setdefault(rep, []).append(i)
    reps = list(members)
    return ExactDuplicates(reps, [m for m in members.values() if len(m) > 1])
