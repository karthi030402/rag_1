"""Step 5: Retrieval. Embed a question and find the most similar stored chunks."""

from typing import Dict, List, Optional

from src import config
from src.embedder import embed_texts
from src.vector_store import get_collection


def retrieve(question: str, top_k: Optional[int] = None) -> List[Dict]:
    top_k = top_k or config.TOP_K
    collection = get_collection()
    query_embedding = embed_texts([question])[0]

    results = collection.query(query_embeddings=[query_embedding], n_results=top_k)

    chunks: List[Dict] = []
    for doc, meta, dist in zip(
        results["documents"][0], results["metadatas"][0], results["distances"][0]
    ):
        chunks.append({
            "text": doc,
            "source": meta["source"],
            "page": meta["page"],
            "distance": dist,
        })
    return chunks
