import os
import subprocess
import sys
from pathlib import Path

import pytest

from contentiq_engine.text import CharShingler, WordShingler, make_shingler, shingle_corpus, stable_hash32


def test_char_shingles():
    assert CharShingler(3).shingles("abcde") == {"abc", "bcd", "cde"}
    assert CharShingler(5).shingles("abc") == {"abc"}
    assert CharShingler(5).shingles("") == set()


def test_word_shingles():
    assert WordShingler(2).shingles("a b c a b") == {"a b", "b c", "c a"}
    assert WordShingler(3).shingles("one two") == {"one two"}
    assert WordShingler(2).shingles("") == set()


def test_ids_are_32_bit_and_match_strings():
    sh = CharShingler(5)
    text = "the quick brown fox jumps"
    ids = sh.shingle_ids(text)
    assert ids == {stable_hash32(s) for s in sh.shingles(text)}
    assert all(0 <= x < 2**32 for x in ids)


def test_ids_identical_across_processes():
    """Built-in hash() is randomized per process; our IDs must not be."""
    code = "from contentiq_engine.text import stable_hash32; print([stable_hash32(s) for s in ['hello', 'naïve', '🔥x']])"
    engine_dir = Path(__file__).resolve().parents[1]
    outputs = set()
    for seed in ("1", "2", "random"):
        env = {**os.environ, "PYTHONHASHSEED": seed, "PYTHONPATH": str(engine_dir)}
        outputs.add(subprocess.check_output([sys.executable, "-c", code], env=env, text=True))
    assert len(outputs) == 1


def test_make_shingler():
    assert isinstance(make_shingler("char"), CharShingler) and make_shingler("char").k == 4
    assert isinstance(make_shingler("word", 3), WordShingler) and make_shingler("word", 3).k == 3
    with pytest.raises(ValueError):
        make_shingler("nope")


def test_shingle_corpus_flags_short_captions():
    texts = ["a long enough caption for comparison", "short", ""]
    sets, flagged = shingle_corpus(texts, CharShingler(5), min_shingles=10)
    assert len(sets) == 3
    assert flagged == [1, 2]
