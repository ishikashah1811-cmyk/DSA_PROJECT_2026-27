import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))

from synthetic import SyntheticDataGenerator  # noqa: E402

from contentiq_engine.dedupe import jaccard  # noqa: E402
from contentiq_engine.text import CharShingler, Preprocessor  # noqa: E402

pre = Preprocessor()


def test_deterministic_for_a_seed():
    a = SyntheticDataGenerator(7).generate(200)
    b = SyntheticDataGenerator(7).generate(200)
    assert a.captions == b.captions and a.planted == b.planted
    assert SyntheticDataGenerator(8).generate(200).captions != a.captions


def test_planted_pairs_point_backwards_and_match_fraction():
    data = SyntheticDataGenerator(1).generate(2000, dup_fraction=0.2)
    assert all(p.source < p.copy for p in data.planted)
    assert len({p.copy for p in data.planted}) == len(data.planted)
    assert 0.15 < len(data.planted) / 2000 < 0.25


def test_originals_are_distinct():
    data = SyntheticDataGenerator(2).generate(1500)
    copies = {p.copy for p in data.planted}
    originals = [pre(c) for i, c in enumerate(data.captions) if i not in copies]
    assert len(set(originals)) == len(originals)


def test_zero_edit_copy_differs_only_cosmetically():
    gen = SyntheticDataGenerator(3)
    for _ in range(20):
        caption, cat = gen.compose_caption()
        copy, n_edits = gen.edit_caption(caption, cat, edit_rate=0.0)
        assert n_edits == 0
        assert pre(copy) == pre(caption)


def test_edit_rate_lowers_similarity():
    gen = SyntheticDataGenerator(4)
    sh = CharShingler(5)
    caption, cat = gen.compose_caption()
    light, _ = gen.edit_caption(caption, cat, 0.05)
    heavy, _ = gen.edit_caption(caption, cat, 0.6)
    orig = sh.shingle_ids(pre(caption))
    assert jaccard(orig, sh.shingle_ids(pre(light))) > jaccard(orig, sh.shingle_ids(pre(heavy)))


def test_base_captions_used_first():
    base = ["first real caption about chai and rain", "second real caption about a long walk"]
    data = SyntheticDataGenerator(5, base_captions=base).generate(20, dup_fraction=0.0)
    assert set(data.captions[:2]) == set(base)


def test_generate_posts_fields():
    posts, data = SyntheticDataGenerator(6).generate_posts(50, n_accounts=4)
    assert len(posts) == 50 == len(data.captions)
    assert set(posts[0]) == {"id", "account", "caption", "timestamp", "likes", "comments", "followers"}
    assert {p["account"] for p in posts} <= {f"acc_{i:02d}" for i in range(4)}
    assert all(p["likes"] >= 0 and p["comments"] >= 0 and p["followers"] > 0 for p in posts)
