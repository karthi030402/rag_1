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
TOP_K = 4               # how many chunks to retrieve per question

# --- Generation ---
# Claude API is used when a key is present; otherwise generation falls back to
# a local Ollama model (free, no key, no internet required).
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GENERATION_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-5")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")
