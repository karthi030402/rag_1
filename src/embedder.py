"""Step 3: Embedding. Turn chunk text into vectors using a local sentence-transformer model."""

from functools import lru_cache
from typing import List

from sentence_transformers import SentenceTransformer

from src import config


@lru_cache(maxsize=1)
def _get_model() -> SentenceTransformer:
    # Cached so the (relatively slow) model load happens only once per process.
    return SentenceTransformer(config.EMBEDDING_MODEL)


def embed_texts(texts: List[str]) -> List[List[float]]:
    model = _get_model()
    vectors = model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
    return vectors.tolist()
