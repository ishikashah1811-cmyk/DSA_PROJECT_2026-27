"""Temporary benchmark data until SyntheticDataGenerator (Person 2) exists.

Random captions from a small vocabulary plus near-copies made with controlled
edits (word delete / insert / swap, character typos). Some captions get
hashtags, mentions, URLs and emoji so the preprocessor is exercised.
"""

from __future__ import annotations

import random

VOCAB = """
morning coffee sunset beach travel vibes weekend new collection launch today sale
offer limited stock hurry shop link bio thank you everyone support love family
friends trip mountains city lights night food dinner recipe homemade cake fresh
summer winter rain monsoon festival celebration birthday wedding outfit style
fashion look fitness workout gym run yoga mindful goals dream hustle work office
team project college exam study notes campus life memories throwback photo shoot
behind scenes studio music dance song cover live stream tonight join us excited
announce giveaway winner comment below tag friend share follow page update soon
coming handmade jewellery earrings necklace gift ideas order now delivery free
shipping across india happy diwali holi eid christmas new year cheers grateful
blessed journey begins chapter small business local artist painting canvas
""".split()

DECOR = ["#travel", "#ootd", "#smallbusiness", "@friend", "https://shop.example/x", "🔥", "✨", "❤️", "😂"]


def _random_caption(rng: random.Random) -> str:
    words = rng.choices(VOCAB, k=rng.randint(10, 25))
    if rng.random() < 0.5:
        words += rng.sample(DECOR, rng.randint(1, 3))
    return " ".join(words)


def _edit(caption: str, rng: random.Random, n_edits: int) -> str:
    words = caption.split()
    for _ in range(n_edits):
        op = rng.choice(("delete", "insert", "swap", "typo"))
        i = rng.randrange(len(words))
        if op == "delete" and len(words) > 3:
            words.pop(i)
        elif op == "insert":
            words.insert(i, rng.choice(VOCAB))
        elif op == "swap" and len(words) > 1:
            j = rng.randrange(len(words))
            words[i], words[j] = words[j], words[i]
        else:
            w = words[i]
            if len(w) > 2:
                k = rng.randrange(len(w))
                words[i] = w[:k] + rng.choice("abcdefghijklmnopqrstuvwxyz") + w[k + 1 :]
    return " ".join(words)


def generate(n: int, dup_fraction: float = 0.1, max_edits: int = 3, seed: int = 42) -> tuple[list[str], list[tuple[int, int]]]:
    """n captions and the planted (original, copy) index pairs."""
    rng = random.Random(seed)
    captions: list[str] = []
    planted: list[tuple[int, int]] = []
    for i in range(n):
        if captions and rng.random() < dup_fraction:
            src = rng.randrange(len(captions))
            captions.append(_edit(captions[src], rng, rng.randint(0, max_edits)))
            planted.append((src, i))
        else:
            captions.append(_random_caption(rng))
    return captions, planted
