"""HashtagTrie: prefix tree over hashtags with counts (plan, Section 2.2).

    insert(tag)                       O(L) for a tag of length L
    find the node for a prefix        O(L)
    completions(prefix) by DFS        O(L + size of the subtree)
    suggest(prefix, k)                O(L + k) from the per-node top-K cache

Each node caches its top-K completions (most used first). The cache is rebuilt
lazily after inserts, in one post-order pass that merges the children's lists.
"""

from __future__ import annotations

from dataclasses import dataclass, field

DEFAULT_CACHE_K = 10


@dataclass
class TrieNode:
    children: dict[str, TrieNode] = field(default_factory=dict)
    count: int = 0  # times the tag ending here was used; 0 if no tag ends here
    top: list[tuple[str, int]] = field(default_factory=list)  # cached top-K (tag, count)


def _rank(item: tuple[str, int]) -> tuple[int, str]:
    tag, count = item
    return (-count, tag)  # most used first, then alphabetical


class HashtagTrie:
    def __init__(self, cache_k: int = DEFAULT_CACHE_K) -> None:
        self.root = TrieNode()
        self.cache_k = cache_k
        self._n_tags = 0
        self._dirty = False

    def __len__(self) -> int:
        """Number of distinct tags."""
        return self._n_tags

    def __contains__(self, tag: str) -> bool:
        return self.count(tag) > 0

    def insert(self, tag: str, times: int = 1) -> None:
        if not tag:
            raise ValueError("empty tag")
        node = self.root
        for ch in tag:
            node = node.children.setdefault(ch, TrieNode())
        if node.count == 0:
            self._n_tags += 1
        node.count += times
        self._dirty = True

    def _find(self, prefix: str) -> TrieNode | None:
        node = self.root
        for ch in prefix:
            node = node.children.get(ch)
            if node is None:
                return None
        return node

    def count(self, tag: str) -> int:
        node = self._find(tag)
        return node.count if node else 0

    def completions(self, prefix: str) -> list[tuple[str, int]]:
        """Every tag starting with prefix, by depth-first search (uncached), ranked."""
        node = self._find(prefix)
        if node is None:
            return []
        out: list[tuple[str, int]] = []
        stack = [(node, prefix)]
        while stack:
            cur, word = stack.pop()
            if cur.count:
                out.append((word, cur.count))
            for ch, child in cur.children.items():
                stack.append((child, word + ch))
        return sorted(out, key=_rank)

    def suggest(self, prefix: str, k: int | None = None) -> list[tuple[str, int]]:
        """Up to k most used tags starting with prefix (k <= cache_k uses the cache)."""
        k = self.cache_k if k is None else k
        if k > self.cache_k:
            return self.completions(prefix)[:k]
        if self._dirty:
            self.rebuild_cache()
        node = self._find(prefix)
        return node.top[:k] if node else []

    def rebuild_cache(self) -> None:
        """Recompute every node's top-K in one post-order pass (iterative)."""
        order: list[tuple[TrieNode, str]] = []
        stack = [(self.root, "")]
        while stack:
            node, word = stack.pop()
            order.append((node, word))
            for ch, child in node.children.items():
                stack.append((child, word + ch))
        for node, word in reversed(order):  # children are always processed before parents
            candidates = [item for child in node.children.values() for item in child.top]
            if node.count:
                candidates.append((word, node.count))
            # At most (children x K + 1) candidates per node, so sorting them is cheap.
            node.top = sorted(candidates, key=_rank)[: self.cache_k]
        self._dirty = False
