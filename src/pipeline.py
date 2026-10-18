"""Step 7: Orchestration. Wires the individual steps into two operations: index and ask."""

from typing import Dict

from src import config
from src.chunker import chunk_pages
from src.embedder import embed_texts
from src.generator import generate_answer
from src.ingest import load_pdfs
from src.retriever import retrieve
from src.vector_store import add_chunks, reset_collection


def build_index() -> int:
    """Full ingestion pipeline: PDF -> pages -> chunks -> embeddings -> vector store."""
    pages = load_pdfs(config.DATA_DIR)
    chunks = chunk_pages(pages)
    embeddings = embed_texts([c["text"] for c in chunks])

    collection = reset_collection()
    add_chunks(collection, chunks, embeddings)
    return len(chunks)


def ask(question: str) -> Dict:
    """Retrieve relevant chunks for a question and generate a grounded answer."""
    context_chunks = retrieve(question)
    answer = generate_answer(question, context_chunks)
    return {"answer": answer, "sources": context_chunks}
