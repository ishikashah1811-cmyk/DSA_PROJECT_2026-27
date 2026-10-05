"""Helpers shared by the ingest adapters."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone

ANON_RE = re.compile(r"^acc_[0-9a-z]+$")
_OFFSET_RE = re.compile(r"([+-]\d{2})(\d{2})$")


def anonymize_account(name: str) -> str:
    """Stable anonymous id for an account; ids already in 'acc_...' form are kept.

    Usernames never reach the database (plan, Section 3: privacy).
    """
    name = (name or "").strip()
    if ANON_RE.match(name):
        return name
    return "acc_" + hashlib.blake2b(name.lower().encode("utf-8"), digest_size=5).hexdigest()


def parse_timestamp(value: object) -> datetime:
    """Unix seconds (number or digit string) or ISO 8601 -> naive UTC datetime.

    Raises ValueError if the value cannot be read.
    """
    if isinstance(value, (int, float)) or (isinstance(value, str) and value.strip().isdigit()):
        return datetime.fromtimestamp(float(value), tz=timezone.utc).replace(tzinfo=None)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"not a timestamp: {value!r}")
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    text = _OFFSET_RE.sub(r"\1:\2", text)  # +0000 -> +00:00 (Graph API style; needed on Python 3.10)
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def fix_mojibake(text: str) -> str:
    """Instagram's JSON export writes UTF-8 bytes as \\u00XX escapes ('CafÃ©' for 'Café').

    Re-encoding as Latin-1 recovers the bytes; text that is already correct is returned unchanged.
    """
    try:
        return text.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text


def stable_post_id(prefix: str, *parts: object) -> str:
    raw = "\x1f".join(str(p) for p in parts)
    return f"{prefix}_" + hashlib.blake2b(raw.encode("utf-8"), digest_size=6).hexdigest()
