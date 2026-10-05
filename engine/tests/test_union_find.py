import random

import pytest

from contentiq_engine.dedupe import UnionFind


def naive_components(n, edges):
    """Reference: repeated relabeling until stable."""
    label = list(range(n))
    changed = True
    while changed:
        changed = False
        for a, b in edges:
            low = min(label[a], label[b])
            if label[a] != low or label[b] != low:
                label[a] = label[b] = low
                changed = True
    groups = {}
    for x in range(n):
        groups.setdefault(label[x], []).append(x)
    return sorted(groups.values())


@pytest.mark.parametrize("seed", range(5))
def test_matches_naive_connected_components(seed):
    rng = random.Random(seed)
    n = 200
    edges = [(rng.randrange(n), rng.randrange(n)) for _ in range(150)]
    uf = UnionFind(n)
    for a, b in edges:
        uf.union(a, b)
    expected = naive_components(n, edges)
    assert sorted(uf.components()) == expected
    assert uf.count == len(expected)


def test_union_and_connected():
    uf = UnionFind(5)
    assert uf.union(0, 1) is True
    assert uf.union(1, 0) is False
    uf.union(3, 4)
    assert uf.connected(0, 1) and not uf.connected(1, 3)
    assert uf.count == 3 and len(uf) == 5


def test_long_chain_no_recursion_error():
    n = 100_000
    uf = UnionFind(n)
    for i in range(n - 1):
        uf.union(i, i + 1)
    assert uf.count == 1 and uf.connected(0, n - 1)
