from functools import lru_cache

from sentence_transformers import CrossEncoder

from app.config import get_settings


class Reranker:
    def __init__(self, model_name: str) -> None:
        self._model = CrossEncoder(model_name)

    def rerank(self, query: str, candidates: list[tuple[str, dict]], top_k: int) -> list[tuple[str, dict, float]]:
        """candidates: list of (text, metadata). Returns top_k (text, metadata, score) sorted desc."""
        if not candidates:
            return []

        pairs = [(query, text) for text, _ in candidates]
        scores = self._model.predict(pairs)

        scored = [
            (text, metadata, float(score))
            for (text, metadata), score in zip(candidates, scores)
        ]
        scored.sort(key=lambda item: item[2], reverse=True)
        return scored[:top_k]


@lru_cache
def get_reranker() -> Reranker:
    return Reranker(get_settings().reranker_model)
