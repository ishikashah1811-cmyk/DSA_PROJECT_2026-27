"""Caption normalization for similarity (plan, Section 2.1 step 1).

Hashtags are removed here so that a shared block of tags does not make unrelated
captions look alike; Module 2 reads hashtags from the raw caption instead.
"""

from __future__ import annotations

import re
import unicodedata

URL_RE = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)
MENTION_RE = re.compile(r"@\w+(?:\.\w+)*")
HASHTAG_RE = re.compile(r"#\w+")
EMOJI_RE = re.compile(
    "["
    "\U0001F000-\U0001FAFF"  # pictographs, emoticons, transport, flags (regional indicators), skin tones
    "←-⇿"  # arrows
    "⌀-⏿"  # misc technical (watch, hourglass, ...)
    "■-➿"  # geometric shapes, misc symbols, dingbats
    "⬀-⯿"  # misc symbols and arrows (star, ...)
    "‍"  # zero-width joiner
    "⃣"  # combining keycap
    "︎️"  # variation selectors
    "\U000E0020-\U000E007F"  # tag characters (subdivision flags)
    "]+"
)
PUNCT_RE = re.compile(r"[^\w\s]")
WHITESPACE_RE = re.compile(r"\s+")


class Preprocessor:
    """Lowercase; remove URLs, @mentions, #hashtags and emoji; collapse whitespace.

    NFKC normalization maps the "fancy font" letters common on Instagram
    (e.g. mathematical bold/script) to plain letters. Removed spans are replaced
    by a space so neighbouring words never merge. Running it twice changes nothing.
    """

    def __init__(self, remove_punctuation: bool = False) -> None:
        self.remove_punctuation = remove_punctuation

    def normalize(self, text: str) -> str:
        text = unicodedata.normalize("NFKC", text).lower()
        text = URL_RE.sub(" ", text)
        text = MENTION_RE.sub(" ", text)
        text = HASHTAG_RE.sub(" ", text)
        text = EMOJI_RE.sub(" ", text)
        if self.remove_punctuation:
            text = PUNCT_RE.sub(" ", text)
        return WHITESPACE_RE.sub(" ", text).strip()

    __call__ = normalize
