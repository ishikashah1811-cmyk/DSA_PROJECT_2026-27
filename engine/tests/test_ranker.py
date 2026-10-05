from datetime import datetime

import pytest

from contentiq_engine.hashtags import HashtagRanker
from contentiq_engine.models import Post


def post(i, tags, likes, comments=0, followers=None):
    caption = "post " + " ".join("#" + t for t in tags)
    return Post(id=str(i), account="a", caption=caption, timestamp=datetime(2026, 1, 1), likes=likes,
                comments=comments, followers=followers)


def test_min_count_drops_rare_tags():
    r = HashtagRanker()
    r.ingest([post(1, ["viral"], 10_000)] + [post(i, ["steady"], 100) for i in range(2, 6)])
    assert [s.tag for s in r.top_k(10, min_count=3)] == ["steady"]
    assert {s.tag for s in r.top_k(10, min_count=1)} == {"viral", "steady"}


def test_smoothing_pulls_small_samples_to_global_mean():
    # One lucky post vs a tag with a strong record over 40 posts.
    posts = [post(0, ["lucky"], 1000)] + [post(i, ["solid"], 300) for i in range(1, 41)]
    r = HashtagRanker()
    r.ingest(posts)
    g = (1000 + 40 * 300) / 41
    assert r.global_mean == pytest.approx(g)
    by_tag = {s.tag: s for s in r.stats(m=5, min_count=1)}
    assert by_tag["lucky"].score == pytest.approx((1000 + 5 * g) / 6)
    assert by_tag["solid"].score == pytest.approx((12000 + 5 * g) / 45)
    # Plain average ranks the lucky tag first; with m = 0 the smoothing is off.
    assert r.top_k(1, m=0, min_count=1)[0].tag == "lucky"
    assert by_tag["lucky"].mean_engagement == 1000 and by_tag["solid"].mean_engagement == 300


def test_follower_normalization_auto():
    small = [post(i, ["small"], 50, followers=1000) for i in range(3)]  # 50 per 1,000 followers
    big = [post(10 + i, ["big"], 500, followers=100_000) for i in range(3)]  # 5 per 1,000 followers
    r = HashtagRanker()
    r.ingest(small + big)
    assert r.normalized
    assert [s.tag for s in r.top_k(2, m=0)] == ["small", "big"]
    raw = HashtagRanker(normalize="none")
    raw.ingest(small + big)
    assert not raw.normalized and [s.tag for s in raw.top_k(2, m=0)] == ["big", "small"]
    partial = HashtagRanker()
    partial.ingest(small + [post(99, ["x"], 1)])  # one post without followers -> raw counts
    assert not partial.normalized


def test_tag_counted_once_per_post_and_ties_alphabetical():
    r = HashtagRanker()
    r.ingest([post(1, ["b", "b", "a"], 10), post(2, ["a", "b"], 10)])
    stats = {s.tag: s for s in r.stats(min_count=1)}
    assert stats["b"].count == 2
    assert [s.tag for s in r.top_k(2, min_count=1)] == ["a", "b"]


def test_top_k_matches_sorted_oracle():
    import random

    rng = random.Random(4)
    tags = [f"t{i}" for i in range(60)]
    posts = [post(i, rng.sample(tags, 3), rng.randint(0, 500), rng.randint(0, 50)) for i in range(400)]
    r = HashtagRanker()
    r.ingest(posts)
    expected = sorted(r.stats(), key=lambda s: (-s.score, -s.count, s.tag))[:15]
    assert r.top_k(15) == expected


def test_invalid_mode():
    with pytest.raises(ValueError):
        HashtagRanker(normalize="likes")
