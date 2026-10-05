"""Settings from environment variables (see .env.example at the repository root)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def _sqlite_path(url: str) -> str:
    prefix = "sqlite:///"
    if not url.startswith(prefix):
        raise ValueError(f"DATABASE_URL must start with {prefix!r}, got {url!r}")
    return url[len(prefix):]


@dataclass
class Settings:
    database_path: str = "contentiq.db"
    cors_origins: list[str] = field(default_factory=lambda: ["http://localhost:3000"])
    seed_sample: bool = True  # load data/sample/sample_posts.csv into an empty database
    sample_path: Path = REPO_ROOT / "data" / "sample" / "sample_posts.csv"
    benchmark_path: Path = REPO_ROOT / "docs" / "benchmarks" / "benchmark.json"
    max_upload_mb: int = 20

    @classmethod
    def from_env(cls) -> Settings:
        env = os.environ
        s = cls()
        if "DATABASE_URL" in env:
            s.database_path = _sqlite_path(env["DATABASE_URL"])
        if "CORS_ORIGINS" in env:
            s.cors_origins = [o.strip() for o in env["CORS_ORIGINS"].split(",") if o.strip()]
        s.seed_sample = _bool(env.get("SEED_SAMPLE"), s.seed_sample)
        if "SAMPLE_PATH" in env:
            s.sample_path = Path(env["SAMPLE_PATH"])
        if "BENCHMARK_PATH" in env:
            s.benchmark_path = Path(env["BENCHMARK_PATH"])
        if "MAX_UPLOAD_MB" in env:
            s.max_upload_mb = int(env["MAX_UPLOAD_MB"])
        return s
