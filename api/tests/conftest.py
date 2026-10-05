import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
for p in (ROOT, ROOT / "engine"):  # works without `pip install -e engine` too
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from fastapi.testclient import TestClient  # noqa: E402

from api.config import Settings  # noqa: E402
from api.main import create_app  # noqa: E402


def make_client(tmp_path, name="test", **overrides):
    folder = tmp_path / name
    folder.mkdir(exist_ok=True)
    settings = Settings(database_path=str(folder / "test.db"), cors_origins=["http://localhost:3000"])
    for key, value in overrides.items():
        setattr(settings, key, value)
    return TestClient(create_app(settings))


@pytest.fixture
def client(tmp_path):
    with make_client(tmp_path) as c:  # seeded with data/sample/sample_posts.csv
        yield c


@pytest.fixture
def empty_client(tmp_path):
    with make_client(tmp_path, "empty", seed_sample=False) as c:
        yield c
