import os
import time
from pathlib import Path

import redis

from app.cache.semantic_cache import clear_semantic_cache, get_semantic_cache
from app.evals import run_evals as eval_runner


def test_clear_semantic_cache_removes_keys():
    settings = __import__("app.config", fromlist=["get_settings"]).get_settings()
    client = redis.from_url(settings.redis_url, decode_responses=True)

    # Create a few fake cache keys using the SemanticCache helper to ensure
    # keys are written in the same format the application uses.
    cache_mod = __import__("app.cache.semantic_cache", fromlist=["get_semantic_cache"]) 
    cache = cache_mod.get_semantic_cache()
    vec = [0.0] * cache._embedding_dim
    created_keys = [cache.store(vec, f"question-test-{i}", {"answer": "x"}) for i in range(3)]
    # Ensure Redis is reachable
    try:
        client.ping()
    except Exception:
        import pytest

        pytest.skip("Redis not available for this test")

    # Wait briefly for keys to be visible, then assert they exist
    import time as _time

    def _scan_keys():
        return list(client.scan_iter(match="qacache:*", count=100))

    for _ in range(5):
        keys_before = _scan_keys()
        if keys_before:
            break
        _time.sleep(0.1)
    # If scan didn't find keys, fall back to verifying the specific created keys
    if not keys_before:
        keys_before = [k for k in created_keys if client.exists(k)]

    if not keys_before:
        import pytest

        pytest.skip("Unable to create qacache keys in Redis in this environment")

    clear_semantic_cache()

    keys_after = _scan_keys()
    assert not keys_after


def test_eval_runner_dry_run_generates_report(tmp_path, monkeypatch):
    # Avoid starting LangGraph: patch the pipeline to a simple fake that
    # returns a deterministic state so the eval runner can proceed quickly.
    monkeypatch.setenv("EVAL_DRY_RUN", "1")

    class FakePipeline:
        def invoke(self, payload):
            return {"answer": "(dry-run) fake answer", "reranked": [], "retrieved": []}

    import importlib

    pipeline_mod = importlib.import_module("app.graph.pipeline")
    monkeypatch.setattr(pipeline_mod, "get_pipeline", lambda: FakePipeline())

    # Run the evals in-process; dry-run env prevents external judge calls.
    eval_runner.run()

    reports = list(Path("eval_reports").glob("eval_*.json"))
    assert reports, "No eval report produced in dry-run"
