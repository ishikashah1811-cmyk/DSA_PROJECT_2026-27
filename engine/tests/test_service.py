from datetime import datetime

import pytest

from contentiq_engine.base import AnalysisResult, AnalyzerModule
from contentiq_engine.models import Post
from contentiq_engine.service import AnalyticsService

POSTS = [
    Post("1", "a", "New summer collection is live now, shop the link in bio! #sale #summer", datetime(2026, 1, 1), 10, 1),
    Post("2", "a", "New summer collection is live now - shop the link in our bio!! #summer", datetime(2026, 1, 2), 20, 2),
    Post("3", "b", "Throwback to our trip to the mountains with the whole family #travel", datetime(2026, 1, 3), 30, 3),
]


class Counter(AnalyzerModule):
    name = "counter"

    def ingest(self, posts):
        self.n = len(posts)

    def run(self, **params):
        return AnalysisResult(self.name, params, {"n": self.n})


def test_default_runs_both_modules():
    svc = AnalyticsService.default()
    svc.ingest(POSTS)
    assert svc.names == ["duplicates", "hashtags"]
    dup = svc.run("duplicates")
    assert dup.data["n_clusters"] == 1
    tags = svc.run("hashtags", min_count=1)
    assert {t["tag"] for t in tags.data["top"]} == {"sale", "summer", "travel"}
    assert svc.suggest("su") == [("summer", 2)]
    assert set(svc.run_all()) == {"duplicates", "hashtags"}


def test_register_late_analyzer_gets_existing_posts():
    svc = AnalyticsService()
    svc.ingest(POSTS)
    svc.register(Counter())
    assert svc.run("counter").data == {"n": 3}
    with pytest.raises(ValueError):
        svc.register(Counter())


def test_unknown_analyzer():
    with pytest.raises(KeyError):
        AnalyticsService().run("nope")
