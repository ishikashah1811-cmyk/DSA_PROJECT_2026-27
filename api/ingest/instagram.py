"""InstagramExportAdapter: Instagram JSON -> list[Post].

Accepted shapes (field names are provisional until a team export is checked,
plan Section 5.3; only this adapter should need to change):

1. "Download your information" export (posts_1.json): a list of posts, each with
   "media": [{"uri", "creation_timestamp", "title"}] and, for carousels, a
   top-level "title" and "creation_timestamp". The caption is the "title".
2. Graph API style: {"data": [...]} or a list of {"id", "caption", "timestamp",
   "like_count", "comments_count"}.

Like and comment counts are read from like_count / likes_count / likes and
comments_count / comment_count / comments when present, otherwise 0.
"""

from __future__ import annotations

import json
from typing import Any

from contentiq_engine.models import Post

from .common import anonymize_account, fix_mojibake, parse_timestamp, stable_post_id

LIKE_KEYS = ("like_count", "likes_count", "likes")
COMMENT_KEYS = ("comments_count", "comment_count", "comments")
CAPTION_KEYS = ("caption", "title", "text")
TIME_KEYS = ("timestamp", "creation_timestamp", "taken_at")


def _first(d: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if d.get(key) not in (None, ""):
            return d[key]
    return None


def _count(value: Any) -> int:
    if isinstance(value, dict):  # Graph API sometimes nests: {"count": n}
        value = value.get("count")
    if isinstance(value, list):  # some exports list the likers
        return len(value)
    return max(0, int(value or 0))


class InstagramExportAdapter:
    source = "instagram"

    def __init__(self, account: str = "acc_export", followers: int | None = None) -> None:
        self.account = anonymize_account(account)
        self.followers = followers

    def parse(self, data: bytes | str) -> tuple[list[Post], int]:
        doc = json.loads(data)
        items = doc.get("data", doc.get("posts", [])) if isinstance(doc, dict) else doc
        if not isinstance(items, list):
            raise ValueError("expected a JSON list of posts or an object with a 'data' list")
        posts: list[Post] = []
        skipped = 0
        for item in items:
            post = self._parse_item(item) if isinstance(item, dict) else None
            if post is None:
                skipped += 1
            else:
                posts.append(post)
        return posts, skipped

    def _parse_item(self, item: dict[str, Any]) -> Post | None:
        media = item.get("media") if isinstance(item.get("media"), list) else []
        first = media[0] if media and isinstance(media[0], dict) else {}
        caption = _first(item, CAPTION_KEYS) or _first(first, CAPTION_KEYS)
        when = _first(item, TIME_KEYS) or _first(first, TIME_KEYS)
        if not caption or when is None:
            return None
        if isinstance(caption, dict):  # older exports: {"text": ...}
            caption = caption.get("text", "")
        caption = fix_mojibake(str(caption))
        try:
            ts = parse_timestamp(when)
            likes = _count(_first(item, LIKE_KEYS))
            comments = _count(_first(item, COMMENT_KEYS))
        except (ValueError, TypeError):
            return None
        post_id = item.get("id") or stable_post_id("ig", self.account, first.get("uri", ""), ts.isoformat(), caption)
        return Post(str(post_id), self.account, caption, ts, likes, comments, self.followers)
