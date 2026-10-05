"""Shared application state: the database and the AnalyticsService holding the posts."""

from __future__ import annotations

import logging
import threading

from fastapi import Request

from contentiq_engine.service import AnalyticsService

from .config import Settings
from .db import Database
from .ingest import CsvAdapter

log = logging.getLogger("contentiq.api")


class AppState:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.db = Database(settings.database_path)
        self.service = AnalyticsService.default()
        self.lock = threading.RLock()  # analyzers keep state, so runs and reloads take turns

    def startup(self) -> None:
        s = self.settings
        if s.seed_sample and self.db.count_posts() == 0 and s.sample_path.exists():
            posts, _ = CsvAdapter().parse(s.sample_path.read_bytes())
            self.db.upsert_posts(posts, source="sample")
            log.info("seeded %d sample posts from %s", len(posts), s.sample_path)
        self.reload()

    def reload(self) -> None:
        """Load every stored post into the engine (after startup and after each import)."""
        with self.lock:
            self.service.ingest(self.db.list_posts())


def get_state(request: Request) -> AppState:
    return request.app.state.ctx
