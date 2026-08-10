import time
from fastapi.testclient import TestClient

from app.main import app
from app.llm import gateway as llm_gateway


client = TestClient(app)


def test_hallucinated_citation_triggers_hard_gate_and_abstains(monkeypatch):
    # Monkeypatch the gateway to always return an answer citing a case that
    # doesn't exist anywhere in the corpus, on every call - including the
    # citation_gate's revision retries, so this exercises the full
    # retry-then-abstain path rather than a lucky first-attempt correction.
    call_count = {"n": 0}

    def fake_generate(question, context, session_id, preferred_model, history="", priority=5):
        call_count["n"] += 1
        return llm_gateway.GatewayResult(
            answer=("In the landmark case Foo v. Bar the Court held that X is true."),
            model_used="test-model",
            prompt_tokens=10,
            completion_tokens=20,
            cost_usd=0.0,
            latency_ms=5.0,
        )

    monkeypatch.setattr(llm_gateway, "generate", fake_generate)

    # Needs a question that actually retrieves real corpus content - reranked
    # empty means generate_node short-circuits before the LLM is even
    # called, which would make this test pass for the wrong reason.
    response = client.post(
        "/query",
        json={
            "question": "What doctrine did Kesavananda Bharati v. State of Kerala establish?",
            "session_id": "rt-halluc-1",
        },
    )
    assert response.status_code == 200
    data = response.json()

    # Hard gate: the fabricated citation never ships as part of an actual
    # answer, even after retries - the final response is the explicit
    # abstention message (which names the rejected citation to explain why
    # it's abstaining - that's transparency, not the failure mode this
    # guards against), not a normal answer asserting "Foo v. Bar" as fact.
    assert "no verified answer is available" in data["answer"]
    assert "Court held that X is true" not in data["answer"]
    assert data["guardrails"]["fabricated_citations"] == ["Foo v. Bar"]
    assert data["guardrails"]["citation_revision_attempts"] == 2
    # generate is called for the initial attempt plus 2 revision retries
    assert call_count["n"] == 3

    assert data["escalated"] is True
    from app.hitl.escalation import get_escalation_queue

    pending = get_escalation_queue().list_pending()
    assert any(
        r["session_id"] == "rt-halluc-1" and "fabricated_citation_hard_gate" in r["reasons"] for r in pending
    )


def test_semantic_cache_hit_skips_generation(monkeypatch):
    q = "What guidelines did the Court lay down in Vishaka v. State of Rajasthan?"
    sid = f"cache-test-{int(time.time())}"
    # Ensure any prior cache entries are cleared so the first call is a miss
    from app.cache.semantic_cache import clear_semantic_cache

    clear_semantic_cache()

    # Monkeypatch generation to a fast deterministic fake so the test is stable
    def fake_generate(question, context, session_id, preferred_model, history="", priority=5):
        return llm_gateway.GatewayResult(
            answer=(
                "The Supreme Court in Vishaka v. State of Rajasthan laid down guidelines to "
                "prevent and address sexual harassment of women at the workplace."
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
