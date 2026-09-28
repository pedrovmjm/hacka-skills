import os
import tempfile


work = tempfile.mkdtemp(prefix="polo-api-tests-")
os.environ["POLO_DB_PATH"] = os.path.join(work, "polo.db")

import pytest
from fastapi.testclient import TestClient

from app import database
from app.main import app


@pytest.fixture(autouse=True)
def clean_database():
    database.reset_database()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def ana_headers():
    return {"X-User": "ana"}

