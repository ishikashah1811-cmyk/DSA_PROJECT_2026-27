"""Request and response shapes of the API contract (plan, Section 5.5)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class Health(BaseModel):
    status: str
    posts: int


class ImportResult(BaseModel):
    imported: int
    skipped: int
    total_posts: int


class PostOut(BaseModel):
    id: str
    account: str
    caption: str
    timestamp: datetime
    hashtags: list[str]
    likes: int
    comments: int
    followers: int | None


class DuplicateRunRequest(BaseModel):
    shingle_type: Literal["char", "word"] = "char"
    k: int = Field(4, ge=1, le=20)
    num_hashes: int = Field(128, ge=1, le=1024)
    bands: int = Field(32, ge=1)
    rows: int = Field(4, ge=1)
    threshold: float = Field(0.6, ge=0.0, le=1.0)
    min_shingles: int = Field(10, ge=0)
    verify: Literal["exact", "fast"] = "exact"
    bucket_cap: int | None = Field(None, ge=2)
    seed: int = 42


class DuplicateRunSummary(BaseModel):
    run_id: int
    n_posts: int
    n_flagged: int
    n_exact_groups: int
    n_candidates: int
    n_pairs: int
    n_clusters: int
    runtime_ms: float


class Cluster(BaseModel):
    cluster_id: int
    size: int
    post_ids: list[str]
    representative_id: str
    representative_caption: str
    min_sim: float
    avg_sim: float


class TagSuggestion(BaseModel):
    tag: str
    count: int


class TagRank(BaseModel):
    tag: str
    count: int
    mean_engagement: float
    score: float


class BenchmarkRow(BaseModel):
    n: int
    brute_ms: float | None
    lsh_ms: float
    recall: float | None
    candidates: int
