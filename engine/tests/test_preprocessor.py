import pytest

from contentiq_engine.text import Preprocessor

pre = Preprocessor()


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("Check https://example.com/x?y=1 NOW", "check now"),
        ("visit www.shop.in today", "visit today"),
        ("thanks @ishika.shah and @team_iq!", "thanks and !"),
        ("Sunset vibes #travel #Goa", "sunset vibes"),
        ("love❤️you 😂😂 so much 👍🏽", "love you so much"),
        ("family 👨‍👩‍👧 time", "family time"),
        ("  lots \n of\t\tspace  ", "lots of space"),
        ("𝐁𝐨𝐥𝐝 Text", "bold text"),
        ("word#tag next", "word next"),
        ("#only #tags", ""),
    ],
)
def test_normalize(raw, expected):
    assert pre.normalize(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "New drop!! 🔥 Shop at https://x.co/abc @brand #sale #style",
        "@@double #  # hash @ alone",
        "Café crème ☕ — c'est la vie 🇫🇷 #paris",
        "ＦＵＬＬＷＩＤＴＨ text and 𝓈𝒸𝓇𝒾𝓅𝓉",
    ],
)
def test_idempotent(raw):
    once = pre.normalize(raw)
    assert pre.normalize(once) == once


def test_remove_punctuation_option():
    assert Preprocessor(remove_punctuation=True)("Hello, world! It's great.") == "hello world it s great"
