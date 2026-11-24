"""Step 7: Orchestration. Wires the individual steps into two operations: index and ask."""

from pathlib import Path
from typing import Dict, Optional

from src import config
from src.chunker import chunk_pages
from src.embedder import embed_texts
from src.generator import generate_answer
from src.ingest import load_pdf, load_pdfs
from src.retriever import retrieve
from src.vector_store import add_chunks, get_collection, is_indexed, reset_collection


def build_index() -> int:
    """Full ingestion pipeline: PDF -> pages -> chunks -> embeddings -> vector store."""
    pages = load_pdfs(config.DATA_DIR)
    chunks = chunk_pages(pages)
    embeddings = embed_texts([c["text"] for c in chunks])

    collection = reset_collection()
    add_chunks(collection, chunks, embeddings)
    return len(chunks)


def add_book(pdf_path: Path) -> Optional[int]:
    """Incremental ingestion: index one PDF into the existing collection.

    Returns the number of chunks added, or None if this file name is already indexed.
    Existing chunks are untouched, so this is much faster than build_index().
    """
    collection = get_collection()
    if is_indexed(collection, pdf_path.name):
        return None
    chunks = chunk_pages(load_pdf(pdf_path))
    embeddings = embed_texts([c["text"] for c in chunks])
    add_chunks(collection, chunks, embeddings)
    return len(chunks)


def ask(question: str) -> Dict:
    """Retrieve relevant chunks for a question and generate a grounded answer."""
    context_chunks = retrieve(question)
    answer = generate_answer(question, context_chunks)
    return {"answer": answer, "sources": context_chunks}
