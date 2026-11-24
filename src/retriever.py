"""Step 5: Retrieval. Embed a question and find the most similar stored chunks."""

from typing import Dict, List, Optional

from src import config
from src.embedder import embed_texts
from src.vector_store import get_collection


def _similarity_pct(distance: float, space: str) -> float:
    """Convert a Chroma distance into cosine similarity as a 0–100 percentage.

    Valid because the embedding model normalizes its vectors to unit length:
      - "l2" (Chroma's default) is SQUARED Euclidean, and for unit vectors
        d = 2 - 2·cos, so cos = 1 - d/2.
      - "cosine" and "ip" distances are both 1 - cos for unit vectors.
    Clamped at 0, since unrelated text can score slightly negative.
    """
    cosine = 1 - distance / 2 if space == "l2" else 1 - distance
    return round(max(0.0, cosine) * 100, 1)


class IndexNotBuiltError(RuntimeError):
    """The vector store is empty, so there is nothing to ground an answer in."""


def retrieve(question: str, top_k: Optional[int] = None) -> List[Dict]:
    top_k = top_k or config.TOP_K
    collection = get_collection()
    if collection.count() == 0:
        raise IndexNotBuiltError("The index is empty. Run `python main.py index` first.")
    query_embedding = embed_texts([question])[0]

    results = collection.query(query_embeddings=[query_embedding], n_results=top_k)
    # Read the metric from the collection itself, not config, so the conversion stays
    # correct for an index built before DISTANCE_METRIC changed. Chroma's default is "l2".
    space = (collection.metadata or {}).get("hnsw:space", "l2")

    chunks: List[Dict] = []
    for doc, meta, dist in zip(
        results["documents"][0], results["metadatas"][0], results["distances"][0]
    ):
        chunks.append({
            "text": doc,
            "source": meta["source"],
            "page": meta["page"],
            "distance": dist,
            "similarity": _similarity_pct(dist, space),
        })
    return chunks
