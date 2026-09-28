import os
import tempfile


work = tempfile.mkdtemp(prefix="agent-platform-tests-")
os.environ["AGENT_DB_PATH"] = os.path.join(work, "agents.db")
os.environ["AGENT_CHECKPOINT_PATH"] = os.path.join(work, "checkpoints.db")

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

