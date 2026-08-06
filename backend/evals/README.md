Eval runner
==========

Quick notes for running the built-in Ragas-style eval runner.

Run locally in dry-run mode (no external LLM calls):

```bash
cd backend
EVAL_DRY_RUN=1 /usr/local/bin/python3 -m app.evals.run_evals
```

Or use the CLI flag:

```bash
cd backend
/usr/local/bin/python3 -m app.evals.run_evals --dry-run
```

The runner writes JSON reports to `backend/eval_reports/`.

CI integration in `.github/workflows/evals.yml` uses the dry-run mode so the job is deterministic and doesn't require secrets.
