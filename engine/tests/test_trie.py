import random
import string

from contentiq_engine.hashtags import HashtagTrie


def reference(counts, prefix):
    return sorted(((t, c) for t, c in counts.items() if t.startswith(prefix)), key=lambda x: (-x[1], x[0]))


def test_insert_count_and_contains():
    trie = HashtagTrie()
    for tag in ["travel", "travel", "travelgram", "trip", "food"]:
        trie.insert(tag)
    assert trie.count("travel") == 2 and trie.count("trav") == 0
    assert "trip" in trie and "tr" not in trie
    assert len(trie) == 4


def test_matches_sorted_list_reference_on_random_tags():
    rng = random.Random(1)
    counts = {}
    trie = HashtagTrie(cache_k=5)
    for _ in range(3000):
        tag = "".join(rng.choice("abcde") for _ in range(rng.randint(1, 6)))
        counts[tag] = counts.get(tag, 0) + 1
        trie.insert(tag)
    for prefix in ["", "a", "ab", "abc", "e", "zz"] + ["".join(rng.choice("abcde") for _ in range(2)) for _ in range(20)]:
        ref = reference(counts, prefix)
        assert trie.completions(prefix) == ref
        assert trie.suggest(prefix) == ref[:5]  # cached path
        assert trie.suggest(prefix, 2) == ref[:2]
        assert trie.suggest(prefix, 50) == ref[:50]  # k above the cache size falls back to DFS


def test_cache_refreshes_after_new_inserts():
    trie = HashtagTrie(cache_k=2)
    trie.insert("goa", 3)
    trie.insert("gold", 1)
    assert trie.suggest("go") == [("goa", 3), ("gold", 1)]
    trie.insert("gym", 5)
    trie.insert("good", 4)
    assert trie.suggest("g") == [("gym", 5), ("good", 4)]
    assert trie.suggest("go") == [("good", 4), ("goa", 3)]


def test_unicode_tags_and_unknown_prefix():
    trie = HashtagTrie()
    trie.insert("café")
    trie.insert("cafe")
    assert {t for t, _ in trie.suggest("caf")} == {"café", "cafe"}
    assert trie.suggest("x") == [] and trie.completions(string.digits) == []
