import os
import time
from pathlib import Path

import redis

from app.cache.semantic_cache import clear_semantic_cache, get_semantic_cache
from app.evals import run_evals as eval_runner


def test_clear_semantic_cache_removes_keys():
    settings = __import__("app.config", fromlist=["get_settings"]).get_settings()
    client = redis.from_url(settings.redis_url, decode_responses=True)

    # Create a few fake cache keys
    for i in range(3):
        client.hset(f"qacache:test-{int(time.time()*1000)}-{i}", mapping={"question": "x", "response_json": "{}", "embedding": b""})

    keys_before = client.keys("qacache:*")
    assert keys_before

    clear_semantic_cache()

    keys_after = client.keys("qacache:*")
    assert not keys_after


def test_eval_runner_dry_run_generates_report(tmp_path, monkeypatch):
    # Ensure dry-run env
    monkeypatch.setenv("EVAL_DRY_RUN", "1")

    # Run the eval runner (writes to backend/eval_reports)
    # Use the module directly; it will honor EVAL_DRY_RUN
    eval_runner.run()

    reports = list(Path("eval_reports").glob("eval_*.json"))
    assert reports, "No eval report produced in dry-run"
