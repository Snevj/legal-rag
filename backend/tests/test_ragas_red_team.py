import time
from fastapi.testclient import TestClient

from app.main import app
from app.llm import gateway as llm_gateway


client = TestClient(app)


def test_hallucinated_citation_triggers_escalation(monkeypatch):
    # Monkeypatch the gateway to return an answer that cites a nonexistent case
    def fake_generate(question, context, session_id, preferred_model, history="", priority=5):
        return llm_gateway.GatewayResult(
            answer=(
                "In the landmark case Foo v. Bar the Court held that X is true."
            ),
            model_used="test-model",
            prompt_tokens=10,
            completion_tokens=20,
            cost_usd=0.0,
            latency_ms=5.0,
        )

    monkeypatch.setattr(llm_gateway, "generate", fake_generate)

    response = client.post("/query", json={"question": "Does X hold?", "session_id": "rt-halluc-1"})
    assert response.status_code == 200
    data = response.json()

    # The guardrails should detect an ungrounded citation. Escalation may
    # either be recorded on the response or present in the escalation queue.
    assert data["guardrails"]["ungrounded_citations"]
    from app.hitl.escalation import get_escalation_queue

    pending = get_escalation_queue().list_pending()
    assert data["escalated"] is True or any(r["session_id"] == "rt-halluc-1" for r in pending)


def test_semantic_cache_hit_skips_generation(monkeypatch):
    q = "What did the Court hold in Gideon v. Wainwright about the right to counsel?"
    sid = f"cache-test-{int(time.time())}"
    # Ensure any prior cache entries are cleared so the first call is a miss
    from app.cache.semantic_cache import clear_semantic_cache

    clear_semantic_cache()

    # Monkeypatch generation to a fast deterministic fake so the test is stable
    def fake_generate(question, context, session_id, preferred_model, history="", priority=5):
        return llm_gateway.GatewayResult(
            answer=(
                "The Supreme Court held in Gideon v. Wainwright that the right to counsel is a "
                "fundamental right and applies to indigent defendants in felony prosecutions."
            ),
            model_used="test-model",
            prompt_tokens=50,
            completion_tokens=20,
            cost_usd=0.0,
            latency_ms=1.0,
        )

    monkeypatch.setattr(llm_gateway, "generate", fake_generate)

    # First call populates the cache
    r1 = client.post("/query", json={"question": q, "session_id": sid})
    assert r1.status_code == 200
    d1 = r1.json()
    assert d1["cache_hit"] is False
    assert d1["prompt_tokens"] >= 0

    # Second call should hit the semantic cache and report zero token usage
    r2 = client.post("/query", json={"question": q, "session_id": sid})
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["cache_hit"] is True
    assert d2["prompt_tokens"] == 0
    assert d2["completion_tokens"] == 0
