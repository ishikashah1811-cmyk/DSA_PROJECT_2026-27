from datetime import datetime

import pytest

from api.ingest import CsvAdapter
from api.ingest.common import anonymize_account, fix_mojibake, parse_timestamp


@pytest.mark.parametrize(
    "value, expected",
    [
        (0, datetime(1970, 1, 1)),
        ("1735725600", datetime(2025, 1, 1, 10, 0)),
        ("2025-01-01T10:00:00", datetime(2025, 1, 1, 10, 0)),
        ("2025-01-01T10:00:00Z", datetime(2025, 1, 1, 10, 0)),
        ("2025-01-01T15:30:00+0530", datetime(2025, 1, 1, 10, 0)),
        ("2025-01-01T15:30:00+05:30", datetime(2025, 1, 1, 10, 0)),
    ],
)
def test_parse_timestamp(value, expected):
    assert parse_timestamp(value) == expected


@pytest.mark.parametrize("bad", ["", "yesterday", None, [1]])
def test_parse_timestamp_rejects(bad):
    with pytest.raises((ValueError, TypeError)):
        parse_timestamp(bad)


def test_anonymize_account():
    a = anonymize_account("Ishika.Shah")
    assert a.startswith("acc_") and a == anonymize_account("ishika.shah") and a != anonymize_account("someone")
    assert anonymize_account("acc_03") == "acc_03"


def test_fix_mojibake_leaves_good_text_alone():
    assert fix_mojibake("CafÃ©") == "Café"
    assert fix_mojibake("Café 🔥") == "Café 🔥"
    assert fix_mojibake("plain") == "plain"


def test_csv_sample_file_loads():
    from api.config import Settings

    posts, skipped = CsvAdapter().parse(Settings().sample_path.read_bytes())
    assert len(posts) == 300 and skipped == 0
    assert all(p.account.startswith("acc_") and p.followers for p in posts)


def test_csv_header_variants_and_bom():
    text = "﻿Caption,Likes\nhello world #hi,7\n"
    posts, skipped = CsvAdapter().parse(text.encode("utf-8"))
    assert skipped == 0 and posts[0].likes == 7 and posts[0].hashtags == ["hi"]
    assert posts[0].id.startswith("csv_")
