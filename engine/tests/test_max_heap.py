import heapq
import random

import pytest

from contentiq_engine.hashtags import MaxHeap


@pytest.mark.parametrize("seed", range(5))
def test_pop_order_matches_heapq_oracle(seed):
    rng = random.Random(seed)
    keys = [rng.randint(-1000, 1000) for _ in range(rng.randint(0, 300))]
    heap = MaxHeap((k, i) for i, k in enumerate(keys))
    oracle = [-k for k in keys]  # heapq is a min-heap: negate the keys
    heapq.heapify(oracle)
    got = [heap.pop()[0] for _ in range(len(keys))]
    assert got == [-heapq.heappop(oracle) for _ in range(len(keys))]
    assert got == sorted(keys, reverse=True)


def test_push_pop_interleaved():
    rng = random.Random(9)
    heap, oracle = MaxHeap(), []
    for _ in range(2000):
        if oracle and rng.random() < 0.4:
            assert heap.pop()[0] == -heapq.heappop(oracle)
        else:
            k = rng.random()
            heap.push(k, None)
            heapq.heappush(oracle, -k)
        assert len(heap) == len(oracle)
        if oracle:
            assert heap.peek()[0] == -oracle[0]


def test_top_k_leaves_heap_unchanged():
    heap = MaxHeap([(3, "c"), (9, "i"), (1, "a"), (7, "g")])
    assert heap.top_k(2) == [(9, "i"), (7, "g")]
    assert heap.top_k(10) == [(9, "i"), (7, "g"), (3, "c"), (1, "a")]
    assert len(heap) == 4 and heap.peek() == (9, "i")


def test_empty_heap_errors():
    heap = MaxHeap()
    assert not heap and heap.top_k(3) == []
    with pytest.raises(IndexError):
        heap.pop()
    with pytest.raises(IndexError):
        heap.peek()
