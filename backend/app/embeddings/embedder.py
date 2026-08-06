from functools import lru_cache
import os

os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("TRANSFORMERS_NO_TF", "1")

from sentence_transformers import SentenceTransformer

from app.config import get_settings

# bge models expect this instruction prefix on the query side (not the
# passage/document side) to get well-calibrated similarity scores.
QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "


class Embedder:
    def __init__(self, model_name: str) -> None:
        self._model = SentenceTransformer(model_name)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors = self._model.encode(texts, normalize_embeddings=True)
        return vectors.tolist()

    def embed_query(self, text: str) -> list[float]:
        vector = self._model.encode(QUERY_INSTRUCTION + text, normalize_embeddings=True)
        return vector.tolist()


@lru_cache
def get_embedder() -> Embedder:
    return Embedder(get_settings().embedding_model)
