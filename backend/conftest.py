import pytest

from app.llm import gateway as llm_gateway


@pytest.fixture(autouse=True, scope="function")
def fake_llm(monkeypatch):
	"""Replace the real LLM gateway with a deterministic fake for tests.

	Tests that need to hit the real API can opt out by patching this fixture.
	"""

	def fake_generate(question, context, session_id, preferred_model=None, history="", priority=5):
		return llm_gateway.GatewayResult(
			answer=f"Simulated answer for: {question}",
			model_used="test-model",
			prompt_tokens=5,
			completion_tokens=5,
			cost_usd=0.0,
			latency_ms=1.0,
		)

	monkeypatch.setattr(llm_gateway, "generate", fake_generate)
	yield

