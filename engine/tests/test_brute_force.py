import random

import pytest

from contentiq_engine.dedupe import BruteForceDetector, MinHasher, SimilarPair, group_exact_duplicates, jaccard


def test_jaccard():
    assert jaccard({1, 2, 3}, {2, 3, 4}) == 0.5
    assert jaccard({1}, {1}) == 1.0
    assert jaccard({1}, {2}) == 0.0
    assert jaccard(set(), set()) == 0.0


def test_find_pairs_matches_naive():
    rng = random.Random(5)
    sets = [set(rng.sample(range(30), rng.randrange(5, 15))) for _ in range(40)]
    t = 0.4
    got = BruteForceDetector(t).find_pairs(sets)
    expected = {(i, j) for i in range(40) for j in range(i + 1, 40) if jaccard(sets[i], sets[j]) >= t}
    assert {(p.a, p.b) for p in got} == expected
    assert all(p.similarity == pytest.approx(jaccard(sets[p.a], sets[p.b])) for p in got)


def test_ids_and_ordering():
    pairs = BruteForceDetector(0.5).find_pairs([{1, 2}, {1, 2}, {9}], ids=["z", "y", "x"])
    assert pairs == [SimilarPair("y", "z", 1.0)]


def test_signature_baseline_agrees_with_estimate():
    rng = random.Random(6)
    sets = [set(rng.sample(range(500), 60)) for _ in range(30)]
    sets += [set(list(s)[3:]) for s in sets[:5]]
    mh = MinHasher(64)
    sigs = mh.signatures(sets)
    det = BruteForceDetector(0.7)
    got = det.find_pairs_signatures(sigs)
    expected = {
        (i, j)
        for i in range(len(sets))
        for j in range(i + 1, len(sets))
        if mh.estimate_jaccard(sigs[i], sigs[j]) >= 0.7
    }
    assert {(p.a, p.b) for p in got} == expected
    assert {(k, 30 + k) for k in range(5)} <= expected


def test_group_exact_duplicates():
    res = group_exact_duplicates(["a b", "c", "a b", "d", "c", "a b"])
    assert res.representatives == [0, 1, 3]
    assert res.groups == [[0, 2, 5], [1, 4]]
