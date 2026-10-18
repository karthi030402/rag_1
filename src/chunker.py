"""Step 2: Chunking. Split page text into overlapping windows sized for embedding."""

from typing import Dict, List

from src import config


def chunk_pages(pages: List[Dict]) -> List[Dict]:
    """Slide a CHUNK_SIZE window over each page's text with CHUNK_OVERLAP overlap.

    Overlap prevents an answer from being split across two chunks with neither
    half containing the full context. Source/page metadata is carried through
    so retrieved chunks can still be cited.
    """
    chunks: List[Dict] = []

    for page in pages:
        text = page["text"]
        start = 0
        while start < len(text):
            end = start + config.CHUNK_SIZE
            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append({
                    "text": chunk_text,
                    "source": page["source"],
                    "page": page["page"],
                })
            if end >= len(text):
                break
            start = end - config.CHUNK_OVERLAP

    return chunks
