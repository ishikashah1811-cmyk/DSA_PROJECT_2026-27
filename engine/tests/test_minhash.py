import random

import numpy as np
import pytest

from contentiq_engine.dedupe import MinHasher, jaccard
from contentiq_engine.dedupe.minhash import EMPTY_VALUE, PRIME


def random_pair(rng, target_j, size=200):
    """Two sets of 32-bit ints with Jaccard close to target_j."""
    shared = int(round(2 * size * target_j / (1 + target_j)))
    pool = rng.sample(range(2**32), shared + 2 * (size - shared))
    common, rest = pool[:shared], pool[shared:]
    return set(common + rest[: size - shared]), set(common + rest[size - shared :])


def test_parameters_fit_uint64():
    mh = MinHasher(128, seed=42)
    assert int(mh.a.min()) >= 1 and int(mh.a.max()) < PRIME
    assert int(mh.b.max()) < PRIME
    assert (PRIME - 1) * (2**32 - 1) + (PRIME - 1) < 2**64


def test_numpy_equals_python_reference():
    mh = MinHasher(64, seed=7)
    rng = random.Random(0)
    for _ in range(20):
        ids = {rng.randrange(2**32) for _ in range(rng.randrange(1, 300))}
        ids |= {0, 2**32 - 1}  # extremes
        assert mh.signature(ids).tolist() == mh.signature_python(ids)


def test_same_seed_same_signature():
    ids = set(range(1000, 1100))
    assert np.array_equal(MinHasher(128, 42).signature(ids), MinHasher(128, 42).signature(ids))
    assert not np.array_equal(MinHasher(128, 42).signature(ids), MinHasher(128, 43).signature(ids))


@pytest.mark.parametrize("target", [0.2, 0.5, 0.8])
def test_estimate_close_to_exact_jaccard(target):
    rng = random.Random(1)
    mh = MinHasher(128, seed=42)
    errors = []
    for _ in range(30):
        x, y = random_pair(rng, target)
        errors.append(mh.estimate_jaccard(mh.signature(x), mh.signature(y)) - jaccard(x, y))
    # Standard error is about sqrt(J(1-J)/128) <= 0.045 per pair; the mean over 30 pairs is much tighter.
    assert abs(np.mean(errors)) < 0.03
    assert max(abs(e) for e in errors) < 0.2


def test_identical_sets_estimate_one():
    mh = MinHasher()
    s = {5, 17, 99, 123456}
    assert mh.estimate_jaccard(mh.signature(s), mh.signature(set(s))) == 1.0


def test_empty_set_and_matrix_shape():
    mh = MinHasher(16)
    assert mh.signature(set()).tolist() == [EMPTY_VALUE] * 16
    assert mh.signature_python(set()) == [EMPTY_VALUE] * 16
    m = mh.signatures([{1, 2}, {3}, set()])
    assert m.shape == (3, 16) and m.dtype == np.uint64
