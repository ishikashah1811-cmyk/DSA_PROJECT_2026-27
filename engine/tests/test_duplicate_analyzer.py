from datetime import datetime

import pytest

from contentiq_engine.base import AnalyzerModule
from contentiq_engine.dedupe import DuplicateAnalyzer
from contentiq_engine.models import Post

TS = datetime(2026, 1, 1)


def post(pid, caption):
    return Post(id=pid, account="acc1", caption=caption, timestamp=TS, likes=10, comments=1)


POSTS = [
    post("p1", "New summer collection is live now, shop the link in bio! #sale"),
    post("p2", "New summer collection is live now - shop the link in our bio!! #fashion"),
    post("p3", "Throwback to our trip to the mountains with the whole family"),
    post("p4", "Throwback to our trip to the mountains with the whole family ❤️ @mom"),
    post("p5", "Monday motivation: drink water, move a little, and be kind to yourself"),
    post("p6", "#tbt #love"),
    post("p7", "#ootd"),
    post("p8", "ok"),
]


def run(**params):
    analyzer = DuplicateAnalyzer()
    analyzer.ingest(POSTS)
    return analyzer.run(**params)


def test_is_analyzer_module():
    assert isinstance(DuplicateAnalyzer(), AnalyzerModule)


def test_finds_near_and_exact_duplicates():
    res = run()
    data = res.data
    clusters = {tuple(c["post_ids"]) for c in data["clusters"]}
    assert ("p1", "p2") in clusters  # near-duplicate (different punctuation and hashtags)
    assert ("p3", "p4") in clusters  # identical after preprocessing
    assert data["n_clusters"] == 2
    assert data["n_posts"] == 8
    assert res.module == "duplicates" and res.runtime_ms >= 0


def test_short_and_empty_captions_are_flagged_not_clustered():
    data = run().data
    # p6 and p7 normalize to "" (exact duplicates of each other) and p8 is too short.
    assert data["flagged_post_ids"] == ["p6", "p7", "p8"]
    assert data["n_flagged"] == 3
    assert all("p6" not in c["post_ids"] for c in data["clusters"])


def test_cluster_report_fields():
    cluster = next(c for c in run().data["clusters"] if "p1" in c["post_ids"])
    assert set(cluster) == {
        "cluster_id", "size", "post_ids", "representative_id", "representative_caption", "min_sim", "avg_sim"
    }
    assert cluster["size"] == 2
    assert 0.6 <= cluster["min_sim"] <= cluster["avg_sim"] <= 1.0


def test_threshold_and_params():
    assert run(threshold=1.0).data["n_clusters"] == 1  # only the exact-duplicate cluster survives
    assert run(shingle_type="word", k=2, min_shingles=3, verify="fast").data["n_clusters"] >= 1
    with pytest.raises(ValueError):
        run(bands=10, rows=4)
    with pytest.raises(ValueError):
        run(not_a_param=1)


def test_empty_input():
    analyzer = DuplicateAnalyzer()
    analyzer.ingest([])
    assert analyzer.run().data["n_clusters"] == 0
