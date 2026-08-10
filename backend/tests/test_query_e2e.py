from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

REPO_ROOT = Path(__file__).resolve().parents[2]
SEED_FILE = REPO_ROOT / "data" / "sample_case_law" / "vishaka_v_state_of_rajasthan.txt"


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
                "What guidelines did the Supreme Court lay down in Vishaka v. "
                "State of Rajasthan regarding sexual harassment at the workplace?"
            )
        },
    )
    assert response.status_code == 200
    data = response.json()

    assert data["answer"].strip()
    assert len(data["sources"]) > 0
    assert any("vishaka" in s["source_title"].lower() for s in data["sources"])


def test_vague_question_about_just_uploaded_document(client):
    # A short, content-free question like "what is this file about" scores
    # near-zero relevance against *any* document under the cross-encoder
    # reranker - including the right one - so corpus-wide retrieval alone
    # can't answer it, especially once the corpus is large enough to crowd
    # out one small upload. session_uploads.py + the split reranking pass
    # in rerank_node exist specifically so this works.
    session_id = "e2e-session-upload-test"
    upload_text = (
        "CURRICULUM VITAE\n\nArjun Mehta\nSoftware Engineer\n\n"
        "Education: B.Tech Computer Science, 2023\n"
        "Experience: Backend Engineer at DataFlow Systems, 2023-2025\n"
        "Skills: Python, distributed systems, Kubernetes\n"
    )
    ingest_response = client.post(
        "/ingest",
        files={"file": ("cv.txt", upload_text.encode(), "text/plain")},
        data={"session_id": session_id},
    )
    assert ingest_response.status_code == 200, ingest_response.text

    response = client.post(
        "/query",
        json={"question": "what is this file about", "session_id": session_id},
    )
    assert response.status_code == 200
    data = response.json()

    # conftest.py fakes the LLM response for all tests, so this can't assert
    # on generated text content - what's actually under test is retrieval:
    # the uploaded doc must reach generate_node as real context (proven by
    # model_used being the faked "test-model", not the no-context
    # short-circuit's "none") and appear in the returned sources.
    assert data["model_used"] == "test-model"
    assert any(s["doc_id"] == ingest_response.json()["doc_id"] for s in data["sources"])
