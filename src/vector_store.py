"""Step 4: Vector store. Persist chunk embeddings in a local Chroma database."""

from typing import Dict, List

import chromadb

from src import config


def _get_client() -> chromadb.ClientAPI:
    config.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(config.STORAGE_DIR))


def get_collection():
    return _get_client().get_or_create_collection(name=config.COLLECTION_NAME)


def reset_collection():
    """Drop and recreate the collection — used when rebuilding the index from scratch."""
    client = _get_client()
    try:
        client.delete_collection(config.COLLECTION_NAME)
    except Exception:
        pass
    return client.get_or_create_collection(name=config.COLLECTION_NAME)


def add_chunks(collection, chunks: List[Dict], embeddings: List[List[float]]) -> None:
    ids = [f"{c['source']}-p{c['page']}-{i}" for i, c in enumerate(chunks)]
    documents = [c["text"] for c in chunks]
    metadatas = [{"source": c["source"], "page": c["page"]} for c in chunks]
    collection.add(ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas)
