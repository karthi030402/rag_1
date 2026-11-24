"""Central configuration for the RAG pipeline. Every other module reads from here."""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"        # put textbook PDFs here
STORAGE_DIR = BASE_DIR / "storage"  # persistent vector DB lives here

# --- Chunking ---
CHUNK_SIZE = 800       # characters per chunk
CHUNK_OVERLAP = 150    # characters shared between consecutive chunks

# --- Embedding ---
EMBEDDING_MODEL = "all-MiniLM-L6-v2"   # small, local, free (via sentence-transformers)

# --- Vector store ---
COLLECTION_NAME = "textbook"
# Chroma distance metric: "cosine", "l2" (squared Euclidean) or "ip". Embeddings are
# unit-normalized, so all three rank results identically; cosine makes
# distance = 1 - cosine similarity directly. Re-run `python main.py index` after changing.
DISTANCE_METRIC = "cosine"
TOP_K = 4               # how many chunks to retrieve per question

# --- Generation ---
# Claude API is used when a key is present; otherwise generation falls back to
# a local Ollama model (free, no key, no internet required).
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GENERATION_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-5-5")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")

# --- API server ---
# When set, /ask requires `Authorization: Bearer <API_TOKEN>`. Leave unset for local-only use.
API_TOKEN = os.getenv("API_TOKEN")
# Used by `python api.py`. 0.0.0.0 lets a real iPhone on the same Wi-Fi connect;
# set API_HOST=127.0.0.1 to accept only connections from this Mac (simulator still works).
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
# Print each /ask question, answer, sources and response JSON in the server terminal.
DEBUG_LOG = os.getenv("DEBUG_LOG", "true").lower() in ("1", "true", "yes")
