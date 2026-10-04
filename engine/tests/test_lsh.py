import random

import numpy as np
import pytest

from contentiq_engine.dedupe import LSHIndex, MinHasher


def test_known_similar_pairs_are_candidates():
    rng = random.Random(3)
    mh = MinHasher(128, seed=42)
    base = [set(rng.sample(range(2**32), 100)) for _ in range(50)]
    near = []
    for s in base[:10]:  # near-copies with Jaccard about 0.9
        lst = list(s)
        near.append(set(lst[5:]) | set(rng.sample(range(2**32), 5)))
    sets = base + near
    index = LSHIndex(bands=32, rows=4)
    index.add_many(range(len(sets)), mh.signatures(sets))
    pairs = index.candidate_pairs()
    for k in range(10):
        assert (k, 50 + k) in pairs
    stats = index.stats
    assert stats.n_docs == 60 and stats.n_candidates == len(pairs)
    # Unrelated random sets almost never collide.
    assert len(pairs) < 10 + 20


def test_query_and_pair_order():
    index = LSHIndex(bands=2, rows=2)
    index.add("b", [1, 2, 3, 4])
    index.add("a", [1, 2, 9, 9])
    index.add("c", [7, 7, 7, 7])
    assert index.candidate_pairs() == {("a", "b")}
    assert index.query([1, 2, 0, 0]) == {"a", "b"}
    assert index.query([0, 0, 3, 4]) == {"b"}


def test_bucket_cap_skips_large_buckets():
    index = LSHIndex(bands=1, rows=2, max_bucket_size=3)
    for i in range(5):
        index.add(i, [1, 1])
    assert index.candidate_pairs() == set()
    assert index.stats.skipped_buckets == 1 and index.stats.largest_bucket == 5


def test_signature_length_checked():
    with pytest.raises(ValueError):
        LSHIndex(bands=4, rows=4).add(0, np.zeros(10, dtype=np.uint64))


@pytest.mark.parametrize(
    "b, r, steep, p03, p05, p06, p08",
    [
        (8, 16, 0.878, 0.000, 0.000, 0.002, 0.204),
        (16, 8, 0.707, 0.001, 0.061, 0.237, 0.947),
        (32, 4, 0.420, 0.229, 0.873, 0.988, 1.000),
        (64, 2, 0.125, 0.998, 1.000, 1.000, 1.000),
    ],
)
def test_formulas_match_plan_table(b, r, steep, p03, p05, p06, p08):
    assert LSHIndex.steep_point(b, r) == pytest.approx(steep, abs=5e-4)
    for s, p in [(0.3, p03), (0.5, p05), (0.6, p06), (0.8, p08)]:
        assert LSHIndex.candidate_probability(s, b, r) == pytest.approx(p, abs=5e-4)
