import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))

from evaluation import connected_components, expand_to_captions, label_scores, pair_scores  # noqa: E402


def test_pair_scores():
    assert pair_scores({(0, 1), (0, 2)}, {(0, 1), (1, 2)}) == (0.5, 0.5)
    assert pair_scores(set(), set()) == (1.0, 1.0)


def test_expand_to_captions():
    # captions 0 and 3 are identical (rep 0); 5 alone (rep 5); doc 0 -> caption 0, doc 1 -> caption 5
    members = {0: [0, 3], 5: [5]}
    got = expand_to_captions([(0, 1)], [0, 5], members, [[0, 3]])
    assert got == {(0, 5), (3, 5), (0, 3)}


def test_connected_components():
    comp = connected_components([(1, 2), (2, 3), (7, 8)])
    assert comp[1] == comp[2] == comp[3]
    assert comp[7] == comp[8] != comp[1]


def test_label_scores_ignores_chained_copies():
    planted = [(0, 1), (1, 2), (5, 6)]  # 2 is a copy of a copy of 0
    predicted = {(0, 1), (0, 2), (3, 4)}  # (0, 2) chained -> ignored; (3, 4) is a false positive
    s = label_scores(predicted, planted)
    assert (s.tp, s.fp, s.fn, s.ignored) == (1, 1, 2, 1)
    assert s.precision == 0.5
    assert s.recall == pytest.approx(1 / 3)
    assert s.f1 == pytest.approx(0.4)
