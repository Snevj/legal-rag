import uuid

from fastapi import APIRouter, HTTPException

from app.cost.budget import BudgetExceededError
from app.graph.pipeline import get_pipeline
from app.llm.gateway import AllModelsUnavailableError, GatewayError, UserThrottledError
from app.memory.chat_history import get_chat_history
from app.models.schemas import GuardrailInfo, QueryRequest, QueryResponse, SourceChunk
from app.tracing.langfuse_client import trace_query

router = APIRouter()


@router.post("/query", response_model=QueryResponse)
def query(request: QueryRequest) -> QueryResponse:
    session_id = request.session_id or uuid.uuid4().hex
    pipeline = get_pipeline()

    with trace_query(request.question, session_id) as span:
        try:
            result = pipeline.invoke(
                {
                    "question": request.question,
                    "session_id": session_id,
                    "priority": request.priority,
                    "request_human_review": request.request_human_review,
                }
            )
        except BudgetExceededError as exc:
            raise HTTPException(status_code=429, detail=str(exc)) from exc
        except UserThrottledError as exc:
            raise HTTPException(status_code=429, detail=str(exc)) from exc
        except AllModelsUnavailableError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except GatewayError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

        sources = [SourceChunk(**item) for item in result.get("reranked", [])]
        input_pii_types = result.get("input_pii_types", [])
        output_pii_types = result.get("output_pii_types", [])

        span.update(
            output={"answer": result["answer"], "cache_hit": result.get("cache_hit", False)},
            metadata={"model_used": result["model_used"], "cost_usd": result["cost_usd"]},
        )

        response = QueryResponse(
            answer=result["answer"],
            sources=sources,
            session_id=session_id,
            model_used=result["model_used"],
            difficulty=result["difficulty"],
            expanded_queries=result.get("expanded_queries", []),
            prompt_tokens=result["prompt_tokens"],
            completion_tokens=result["completion_tokens"],
            cost_usd=result["cost_usd"],
            latency_ms=result["latency_ms"],
            cache_hit=result.get("cache_hit", False),
            guardrails=GuardrailInfo(
                input_pii_detected=bool(input_pii_types),
                input_pii_types=input_pii_types,
                injection_flagged=result.get("injection_flagged", False),
                output_pii_detected=bool(output_pii_types),
                output_pii_types=output_pii_types,
                grounding_score=result.get("grounding_score", 0.0),
                ungrounded_citations=result.get("ungrounded_citations", []),
                disclaimer_added=result.get("disclaimer_added", False),
                fabricated_citations=result.get("fabricated_citations", []),
                citation_revision_attempts=result.get("citation_check_attempts", 0),
            ),
            escalated=result.get("escalated", False),
            escalation_reasons=result.get("escalation_reasons", []),
        )

        get_chat_history().append(session_id, request.question, response.model_dump())
        return response
