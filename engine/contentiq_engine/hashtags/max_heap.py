"""MaxHeap: binary max-heap stored in a Python list (plan, Section 2.2).

The children of index i are 2i+1 and 2i+2; the parent of i is (i-1)//2.
Items are (key, value) pairs ordered by key; keys must be mutually comparable.
Python's heapq (a min-heap) is used only as a test oracle.

    heapify (build from n items, bottom-up)   O(n)
    push / pop                                O(log n)
    peek                                      O(1)
    top K (K pops)                            O(K log n)
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Generic, TypeVar

V = TypeVar("V")


class MaxHeap(Generic[V]):
    def __init__(self, items: Iterable[tuple[Any, V]] = ()) -> None:
        self._a: list[tuple[Any, V]] = list(items)
        # Bottom-up heapify: sift down every internal node, last parent first. O(n) overall.
        for i in range(len(self._a) // 2 - 1, -1, -1):
            self._sift_down(i)

    def __len__(self) -> int:
        return len(self._a)

    def __bool__(self) -> bool:
        return bool(self._a)

    def push(self, key: Any, value: V) -> None:
        self._a.append((key, value))
        self._sift_up(len(self._a) - 1)

    def peek(self) -> tuple[Any, V]:
        if not self._a:
            raise IndexError("peek from an empty heap")
        return self._a[0]

    def pop(self) -> tuple[Any, V]:
        """Remove and return the item with the largest key."""
        if not self._a:
            raise IndexError("pop from an empty heap")
        top = self._a[0]
        last = self._a.pop()
        if self._a:
            self._a[0] = last
            self._sift_down(0)
        return top

    def top_k(self, k: int) -> list[tuple[Any, V]]:
        """The k largest items in descending order. Leaves the heap unchanged."""
        copy = MaxHeap.__new__(MaxHeap)
        copy._a = list(self._a)  # already a valid heap; O(n) copy, then k pops
        return [copy.pop() for _ in range(min(k, len(copy)))]

    def _sift_up(self, i: int) -> None:
        a = self._a
        item = a[i]
        while i > 0:
            parent = (i - 1) // 2
            if a[parent][0] >= item[0]:
                break
            a[i] = a[parent]
            i = parent
        a[i] = item

    def _sift_down(self, i: int) -> None:
        a = self._a
        n = len(a)
        item = a[i]
        while True:
            child = 2 * i + 1
            if child >= n:
                break
            if child + 1 < n and a[child + 1][0] > a[child][0]:
                child += 1  # larger of the two children
            if item[0] >= a[child][0]:
                break
            a[i] = a[child]
            i = child
        a[i] = item
