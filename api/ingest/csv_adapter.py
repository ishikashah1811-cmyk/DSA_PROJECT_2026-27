"""CsvAdapter: CSV of posts -> list[Post].

Columns: caption (required), id, account, timestamp, likes, comments, followers.
The column names match the posts table, so data/sample/sample_posts.csv loads as is.
"""

from __future__ import annotations

import csv
import io
from datetime import datetime, timezone

from contentiq_engine.models import Post

from .common import anonymize_account, parse_timestamp, stable_post_id


class CsvAdapter:
    source = "csv"

    def __init__(self, default_account: str = "acc_upload") -> None:
        self.default_account = default_account

    def parse(self, data: bytes | str) -> tuple[list[Post], int]:
        """Returns (posts, number of skipped rows). Rows without a caption or with an
        unreadable timestamp or count are skipped."""
        text = data.decode("utf-8-sig") if isinstance(data, bytes) else data
        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames or "caption" not in [f.strip().lower() for f in reader.fieldnames]:
            raise ValueError("CSV needs a header row with a 'caption' column")
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        posts: list[Post] = []
        skipped = 0
        for raw in reader:
            row = {(k or "").strip().lower(): (v or "").strip() for k, v in raw.items()}
            caption = row.get("caption", "")
            if not caption:
                skipped += 1
                continue
            try:
                ts = parse_timestamp(row["timestamp"]) if row.get("timestamp") else now
                likes = int(float(row.get("likes") or 0))
                comments = int(float(row.get("comments") or 0))
                followers = int(float(row["followers"])) if row.get("followers") else None
            except ValueError:
                skipped += 1
                continue
            if likes < 0 or comments < 0 or (followers is not None and followers <= 0):
                skipped += 1
                continue
            account = anonymize_account(row.get("account") or self.default_account)
            post_id = row.get("id") or stable_post_id("csv", account, ts.isoformat(), caption)
            posts.append(Post(post_id, account, caption, ts, likes, comments, followers))
        return posts, skipped
