from functools import lru_cache

from langgraph.graph import END, StateGraph

from app.graph.nodes import (
    cache_lookup_node,
    cache_store_node,
    citation_gate_node,
    escalation_node,
    generate_node,
    input_guardrail_node,
    memory_load_node,
    memory_store_node,
    output_guardrail_node,
    rerank_node,
    retrieve_node,
    route_node,
)
from app.graph.state import RagState


def _route_by_cache_hit(state: RagState) -> str:
    return "hit" if state.get("cache_hit") else "miss"


def _route_by_citation_check(state: RagState) -> str:
    return "retry" if state.get("citation_check_retry") else "continue"


def build_pipeline():
    graph = StateGraph(RagState)
    graph.add_node("route", route_node)
    graph.add_node("input_guardrail", input_guardrail_node)
    graph.add_node("memory_load", memory_load_node)
    graph.add_node("cache_lookup", cache_lookup_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("rerank", rerank_node)
    graph.add_node("generate", generate_node)
    graph.add_node("citation_gate", citation_gate_node)
    graph.add_node("output_guardrail", output_guardrail_node)
    graph.add_node("escalation", escalation_node)
    graph.add_node("memory_store", memory_store_node)
    graph.add_node("cache_store", cache_store_node)

    graph.set_entry_point("route")
    graph.add_edge("route", "input_guardrail")
    graph.add_edge("input_guardrail", "memory_load")
    graph.add_edge("memory_load", "cache_lookup")

    # A cache hit skips straight to recording the turn in memory and ending;
    # a miss runs the full retrieve/rerank/generate/guardrail pipeline and
    # then also stores the result in the semantic cache for next time.
    graph.add_conditional_edges("cache_lookup", _route_by_cache_hit, {"hit": "memory_store", "miss": "retrieve"})

    graph.add_edge("retrieve", "rerank")
    graph.add_edge("rerank", "generate")
    graph.add_edge("generate", "citation_gate")

    # Hard gate: a citation with zero match anywhere in the corpus loops
    # back to regenerate (up to citation_gate_node's attempt cap) instead of
    # shipping an answer that cites a case that may not exist.
    graph.add_conditional_edges(
        "citation_gate", _route_by_citation_check, {"retry": "generate", "continue": "output_guardrail"}
    )

    graph.add_edge("output_guardrail", "escalation")
    graph.add_edge("escalation", "memory_store")

    graph.add_conditional_edges("memory_store", _route_by_cache_hit, {"hit": END, "miss": "cache_store"})
    graph.add_edge("cache_store", END)

    return graph.compile()


@lru_cache
def get_pipeline():
    return build_pipeline()
