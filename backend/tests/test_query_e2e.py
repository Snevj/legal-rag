from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

REPO_ROOT = Path(__file__).resolve().parents[2]
SEED_FILE = REPO_ROOT / "data" / "sample_case_law" / "gideon_v_wainwright.txt"


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def seeded_corpus(client):
    with open(SEED_FILE, "rb") as f:
        response = client.post("/ingest", files={"file": (SEED_FILE.name, f, "text/plain")})
    assert response.status_code == 200, response.text
    return response.json()


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["redis_connected"] is True


def test_query_returns_grounded_answer(client):
    response = client.post(
        "/query",
        json={
            "question": (
                "What did the Supreme Court hold in Gideon v. Wainwright "
                "about the right to counsel?"
            )
        },
    )
    assert response.status_code == 200
    data = response.json()

    assert data["answer"].strip()
    assert len(data["sources"]) > 0
    assert any("gideon" in s["source_title"].lower() for s in data["sources"])
