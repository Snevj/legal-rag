"""Ragas-style RAG eval metrics (faithfulness, answer relevancy, context
precision, context recall), implemented directly against Groq + our local
embedder rather than the `ragas` PyPI package.

Why not the `ragas` package: as of the version available at implementation
time, `import ragas` unconditionally imports `langchain_community`'s
VertexAI chat model integration, which pulls in Google Cloud's AI Platform
SDK even though we never use it - directly working against the point of
keeping this image small enough not to OOM on an AWS free-tier instance.
These implementations follow the same methodology (LLM-as-judge scoring,
0.0-1.0 scale) at a fraction of the dependency weight.
"""

import json
import re

import numpy as np
from groq import APIConnectionError, APITimeoutError, Groq, InternalServerError, RateLimitError
from tenacity import Retrying, retry_if_exception_type, stop_after_attempt, wait_random_exponential

from app.config import get_settings
from app.embeddings.embedder import get_embedder
import os

_JUDGE_SYSTEM_PROMPT = (
    "You are a strict evaluation assistant. Respond with ONLY a single valid "
    "JSON object, no other text, no markdown code fences."
)

# Judge calls are raw Groq calls outside app.llm.gateway (this script isn't
# the RAG pipeline, and the judge shouldn't compete with real user queries
# for the same resilience budget) - but that means they need their own
# backoff, or a batch run like this one will blow straight through Groq's
# real TPM limit, exactly the "cost blowup" the gateway exists to prevent.
_RETRYABLE_ERRORS = (RateLimitError, APIConnectionError, APITimeoutError, InternalServerError)


def _ask_judge(prompt: str) -> dict:
    # Dry-run shortcut for CI / local testing without a Groq API key
    if os.environ.get("EVAL_DRY_RUN", "0") == "1":
        # Simple heuristics to return plausible JSON without calling Groq
        if "Generate exactly 3 short questions" in prompt:
            # Try to extract a short answer snippet to form questions
            m = re.search(r"ANSWER:\n(.+)", prompt, re.DOTALL)
            answer_snip = (m.group(1).strip().split(".")[0]) if m else "the answer"
            return {"questions": [f"What is {answer_snip}?", f"Explain {answer_snip}.", f"Describe {answer_snip}."]}
        if "Is the following CHUNK relevant" in prompt:
            return {"relevant": True}
        # Default numeric scorer
        return {"score": 1.0}

    settings = get_settings()
    client = Groq(api_key=settings.groq_api_key)

    def _call() -> str:
        completion = client.chat.completions.create(
            # Cheap model: judging (short yes/no or 0-1 scores) doesn't need
            # the expensive model, and it keeps eval runs off the same TPM
            # bucket real hard user queries use.
            model=settings.groq_model_cheap,
            messages=[
                {"role": "system", "content": _JUDGE_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
        )
        return completion.choices[0].message.content or "{}"

    retryer = Retrying(
        retry=retry_if_exception_type(_RETRYABLE_ERRORS),
        wait=wait_random_exponential(multiplier=1.0, max=20),
        stop=stop_after_attempt(5),
        reraise=True,
    )
    text = retryer(_call)

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return {}
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}


def faithfulness(answer: str, context: str) -> float:
    """Does every factual claim in the answer come from the context?"""
    prompt = (
        "Rate how faithful the ANSWER is to the CONTEXT: does every factual claim "
        "in the answer come from the context, with no fabrication?\n"
        'Respond as JSON: {"score": <float 0.0-1.0>, "reasoning": "<one sentence>"}\n\n'
        f"CONTEXT:\n{context}\n\nANSWER:\n{answer}"
    )
    return float(_ask_judge(prompt).get("score", 0.0))


def answer_relevancy(question: str, answer: str) -> float:
    """Does the answer actually address the question asked (vs. tangential)?
    Ragas' approach: have the judge reverse-generate questions the answer
    would fit, then compare their embeddings to the real question."""
    embedder = get_embedder()
    prompt = (
        "Generate exactly 3 short questions that the following ANSWER would be a "
        "direct, complete response to.\n"
        'Respond as JSON: {"questions": ["...", "...", "..."]}\n\n'
        f"ANSWER:\n{answer}"
    )
    generated_questions = _ask_judge(prompt).get("questions", [])
    if not generated_questions:
        return 0.0

    question_vec = np.array(embedder.embed_query(question))
    similarities = []
    for generated_question in generated_questions:
        candidate_vec = np.array(embedder.embed_query(generated_question))
        denom = np.linalg.norm(question_vec) * np.linalg.norm(candidate_vec) + 1e-8
        similarities.append(float(np.dot(question_vec, candidate_vec) / denom))
    return sum(similarities) / len(similarities)


def context_precision(question: str, retrieved_chunks: list[str]) -> float:
    """Of the retrieved chunks, what fraction are actually relevant?"""
    if not retrieved_chunks:
        return 0.0
    relevant = 0
    for chunk in retrieved_chunks:
        prompt = (
            "Is the following CHUNK relevant to answering the QUESTION?\n"
            'Respond as JSON: {"relevant": true or false}\n\n'
            f"QUESTION:\n{question}\n\nCHUNK:\n{chunk}"
        )
        if _ask_judge(prompt).get("relevant") is True:
            relevant += 1
    return relevant / len(retrieved_chunks)


def context_recall(reference_answer: str, context: str) -> float:
    """What fraction of the reference answer's claims are supported by the
    retrieved context? (i.e. did retrieval find what was needed at all)"""
    prompt = (
        "Does the CONTEXT contain enough information to support every claim in "
        "the REFERENCE ANSWER? Rate the fraction of the reference answer's claims "
        "that are supported.\n"
        'Respond as JSON: {"score": <float 0.0-1.0>, "reasoning": "<one sentence>"}\n\n'
        f"CONTEXT:\n{context}\n\nREFERENCE ANSWER:\n{reference_answer}"
    )
    return float(_ask_judge(prompt).get("score", 0.0))
