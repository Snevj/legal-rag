import json
import time
from pathlib import Path

from app.evals.dataset import EVAL_DATASET
from app.evals.metrics import answer_relevancy, context_precision, context_recall, faithfulness
from app.graph.pipeline import get_pipeline

REPORT_DIR = Path("eval_reports")


def _format_context(reranked: list[dict]) -> str:
    return "\n\n---\n\n".join(f"[{c['source_title']}]\n{c['text']}" for c in reranked)


def run() -> None:
    pipeline = get_pipeline()
    results = []
    # Unique per run: an intentional batch eval shouldn't share (and exhaust)
    # the same per-session daily token budget across repeated runs - that
    # cap exists to stop one interactive user from hogging quota, not to
    # throttle a deliberate admin job. The global daily budget still applies.
    run_session_id = f"eval-runner-{int(time.time())}"

    for i, case in enumerate(EVAL_DATASET, start=1):
        print(f"[{i}/{len(EVAL_DATASET)}] {case.question}")
        state = pipeline.invoke({"question": case.question, "session_id": run_session_id, "priority": 1})

        answer = state["answer"]
        reranked = state.get("reranked", [])
        context = _format_context(reranked)
        chunk_texts = [c["text"] for c in reranked]
        retrieved_doc_ids = {c["doc_id"] for c in reranked}

        scores = {
            "faithfulness": faithfulness(answer, context),
            "answer_relevancy": answer_relevancy(case.question, answer),
            "context_precision": context_precision(case.question, chunk_texts),
            "context_recall": context_recall(case.reference_answer, context),
            "retrieved_expected_doc": case.expected_doc_id in retrieved_doc_ids,
        }

        print(
            f"  faithfulness={scores['faithfulness']:.2f} "
            f"relevancy={scores['answer_relevancy']:.2f} "
            f"precision={scores['context_precision']:.2f} "
            f"recall={scores['context_recall']:.2f} "
            f"retrieved_expected={scores['retrieved_expected_doc']}"
        )

        results.append(
            {
                "question": case.question,
                "answer": answer,
                "reference_answer": case.reference_answer,
                **scores,
            }
        )

    def _avg(key: str) -> float:
        return sum(r[key] for r in results) / len(results)

    summary = {
        "num_cases": len(results),
        "avg_faithfulness": _avg("faithfulness"),
        "avg_answer_relevancy": _avg("answer_relevancy"),
        "avg_context_precision": _avg("context_precision"),
        "avg_context_recall": _avg("context_recall"),
        "retrieval_hit_rate": sum(1 for r in results if r["retrieved_expected_doc"]) / len(results),
    }

    print("\n=== Summary ===")
    for key, value in summary.items():
        print(f"{key}: {value}")

    REPORT_DIR.mkdir(exist_ok=True)
    report_path = REPORT_DIR / f"eval_{int(time.time())}.json"
    report_path.write_text(json.dumps({"summary": summary, "results": results}, indent=2))
    print(f"\nSaved report to {report_path}")


if __name__ == "__main__":
    run()
