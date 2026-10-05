import numpy as np
import pytest

from contentiq_engine.dedupe import DuplicateClusterer, MinHasher, SimilarPair


def test_verify_exact_keeps_pairs_above_threshold():
    sets = [{1, 2, 3, 4}, {1, 2, 3, 5}, {9}]
    kept = DuplicateClusterer(0.5).verify({(0, 1), (0, 2)}, shingle_sets=sets)
    assert kept == [SimilarPair(0, 1, 0.6)]


def test_verify_fast_uses_signatures():
    mh = MinHasher(64)
    sets = [set(range(100)), set(range(5, 105)), set(range(500, 600))]
    sigs = mh.signatures(sets)
    kept = DuplicateClusterer(0.7, verify="fast").verify({(0, 1), (1, 2)}, signatures=sigs)
    assert [(p.a, p.b) for p in kept] == [(0, 1)]


def test_verify_needs_matching_input():
    with pytest.raises(ValueError):
        DuplicateClusterer(verify="exact").verify({(0, 1)}, signatures=np.zeros((2, 4)))
    with pytest.raises(ValueError):
        DuplicateClusterer(verify="nope")


def test_cluster_reports_chain_and_stats():
    edges = [SimilarPair(0, 1, 0.9), SimilarPair(1, 2, 0.7), SimilarPair(4, 5, 0.8)]
    clusters = DuplicateClusterer.cluster(6, edges)
    assert [c.members for c in clusters] == [[0, 1, 2], [4, 5]]
    big = clusters[0]
    assert big.size == 3 and big.representative == 1  # 1 is linked to both others
    assert big.min_sim == 0.7 and big.avg_sim == pytest.approx(0.8)
    assert big.n_edges == 2
    assert [c.cluster_id for c in clusters] == [0, 1]


def test_cluster_no_edges():
    assert DuplicateClusterer.cluster(3, []) == []
