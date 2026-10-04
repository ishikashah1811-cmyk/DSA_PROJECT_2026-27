"""Union-Find (disjoint set union) with path compression and union by rank.

Elements are the integers 0 .. n-1. With both optimizations the amortized cost
per operation is O(alpha(n)) (inverse Ackermann), effectively constant.
"""

from __future__ import annotations


class UnionFind:
    def __init__(self, n: int) -> None:
        if n < 0:
            raise ValueError("n must be >= 0")
        self._parent = list(range(n))
        self._rank = [0] * n
        self._count = n

    def __len__(self) -> int:
        return len(self._parent)

    @property
    def count(self) -> int:
        """Number of disjoint sets."""
        return self._count

    def find(self, x: int) -> int:
        """Root of x's set. Iterative, so deep trees cannot hit the recursion limit."""
        root = x
        while self._parent[root] != root:
            root = self._parent[root]
        while self._parent[x] != root:  # path compression: point every node on the path at the root
            self._parent[x], x = root, self._parent[x]
        return root

    def union(self, x: int, y: int) -> bool:
        """Merge the sets of x and y. Returns False if they were already together."""
        rx, ry = self.find(x), self.find(y)
        if rx == ry:
            return False
        if self._rank[rx] < self._rank[ry]:  # union by rank: attach the shorter tree under the taller
            rx, ry = ry, rx
        self._parent[ry] = rx
        if self._rank[rx] == self._rank[ry]:
            self._rank[rx] += 1
        self._count -= 1
        return True

    def connected(self, x: int, y: int) -> bool:
        return self.find(x) == self.find(y)

    def components(self) -> list[list[int]]:
        """All sets, each sorted, ordered by their smallest element."""
        groups: dict[int, list[int]] = {}
        for x in range(len(self._parent)):
            groups.setdefault(self.find(x), []).append(x)
        return list(groups.values())
