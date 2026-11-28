"""Step 4: Vector store. Persist chunk embeddings in a local Chroma database."""

import shutil
import sqlite3
import uuid
from contextlib import closing
from typing import Dict, List

import chromadb

from src import config


def _get_client() -> chromadb.ClientAPI:
    config.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(config.STORAGE_DIR))


def _collection_metadata() -> Dict:
    # The distance metric is fixed when a collection is created; changing
    # config.DISTANCE_METRIC only takes effect after `python main.py index`.
    return {"hnsw:space": config.DISTANCE_METRIC}


def get_collection():
    return _get_client().get_or_create_collection(
        name=config.COLLECTION_NAME, metadata=_collection_metadata()
    )


def reset_collection():
    """Drop and recreate the collection — used when rebuilding the index from scratch."""
    client = _get_client()
    try:
        client.delete_collection(config.COLLECTION_NAME)
    except Exception:
        pass
    return client.get_or_create_collection(
        name=config.COLLECTION_NAME, metadata=_collection_metadata()
    )


def remove_orphan_segment_dirs() -> List[str]:
    """Delete vector-index folders left behind by previously deleted collections.

    Chroma's delete_collection() drops the collection from chroma.sqlite3 but leaves
    its HNSW folder (storage/<segment-uuid>/) on disk, so every full re-index used to
    leave one more stale folder. A folder is kept only if chroma.sqlite3 still lists
    its UUID as a live segment. Returns the names of the folders removed.
    """
    db_path = config.STORAGE_DIR / "chroma.sqlite3"
    if not db_path.exists():
        return []
    with closing(sqlite3.connect(db_path)) as conn:
        live = {row[0] for row in conn.execute("SELECT id FROM segments")}

    removed = []
    for path in config.STORAGE_DIR.iterdir():
        if not path.is_dir() or path.name in live:
            continue
        try:
            uuid.UUID(path.name)  # only ever touch Chroma's UUID-named segment folders
        except ValueError:
            continue
        shutil.rmtree(path)
        removed.append(path.name)
    return removed


def add_chunks(collection, chunks: List[Dict], embeddings: List[List[float]]) -> None:
    ids = [f"{c['source']}-p{c['page']}-{i}" for i, c in enumerate(chunks)]
    documents = [c["text"] for c in chunks]
    metadatas = [{"source": c["source"], "page": c["page"]} for c in chunks]
    collection.add(ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas)


def is_indexed(collection, source: str) -> bool:
    """True if any chunk from this PDF file name is already stored."""
    return bool(collection.get(where={"source": source}, limit=1)["ids"])
