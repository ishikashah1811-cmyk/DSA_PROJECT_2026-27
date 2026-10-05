from datetime import datetime

from contentiq_engine.base import AnalyzerModule
from contentiq_engine.hashtags import HashtagAnalyzer
from contentiq_engine.models import Post


def make_posts():
    rows = [
        ("Beach day #Travel #goa", 120), ("Sunset #travel #beach", 80), ("Chai time #chai #travel", 40),
        ("Road trip #roadtrip #travel", 200), ("Goa again #goa #beach", 60), ("Waves #beach", 90),
        ("More chai #chai", 10), ("Chai and rain #chai #monsoon", 30),
    ]
    return [Post(str(i), "acc", c, datetime(2026, 1, 1), likes, 0) for i, (c, likes) in enumerate(rows)]


def test_is_analyzer_module():
    assert isinstance(HashtagAnalyzer(), AnalyzerModule)


def test_run_reports_top_tags():
    a = HashtagAnalyzer()
    a.ingest(make_posts())
    res = a.run(k=5, min_count=3)
    top = res.data["top"]
    assert {t["tag"] for t in top} == {"travel", "beach", "chai"}  # goa (2) and others are below min_count
    assert set(top[0]) == {"tag", "count", "mean_engagement", "score"}
    assert top == sorted(top, key=lambda t: -t["score"])
    assert res.data["n_tags"] == 6 and res.data["engagement_unit"] == "likes_plus_comments"
    assert res.module == "hashtags"


def test_suggest_ignores_hash_and_case():
    a = HashtagAnalyzer()
    a.ingest(make_posts())
    assert a.suggest("#TR") == [("travel", 4)]
    assert a.suggest("b", 1) == [("beach", 3)]
    assert a.suggest("c") == [("chai", 3)]
    assert a.suggest("zzz") == []


def test_reingest_replaces_state():
    a = HashtagAnalyzer()
    a.ingest(make_posts())
    a.ingest(make_posts()[:1])
    assert a.suggest("t") == [("travel", 1)]
