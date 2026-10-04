"""Shared domain entity (plan, Section 5.3). Field names are provisional until a
real export sample is checked; only the ingest adapters should need to change."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime

HASHTAG_RE = re.compile(r"#(\w+)")


def extract_hashtags(caption: str) -> list[str]:
    """Hashtags in order of appearance, lowercased, without the '#'."""
    return [tag.lower() for tag in HASHTAG_RE.findall(caption)]


@dataclass
class Post:
    id: str
    account: str  # anonymized
    caption: str
    timestamp: datetime
    likes: int
    comments: int
    followers: int | None = None
    hashtags: list[str] = field(default_factory=list)  # derived from caption

    def __post_init__(self) -> None:
        if not self.hashtags:
            self.hashtags = extract_hashtags(self.caption)
