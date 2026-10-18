# Textbook RAG — Retrieval-Augmented Q&A

A Retrieval-Augmented Generation (RAG) system that answers questions about a textbook
(or any PDF) by retrieving the relevant passages and grounding an LLM's answer in them,
with page-number citations.

## How it works

```
PDF textbook
     │  (src/ingest.py)
     ▼
Raw text per page
     │  (src/chunker.py)
     ▼
Overlapping text chunks  ──────────────┐
     │  (src/embedder.py)              │
     ▼                                 │
Chunk embeddings                       │  metadata: source file + page number
     │  (src/vector_store.py)          │  carried through every step, so the
     ▼                                 │  final answer can cite where it came from
Chroma vector database  ◄──────────────┘
     │
     │  question comes in
     ▼
src/retriever.py  → embeds the question, finds top-k nearest chunks
     │
     ▼
src/generator.py  → sends question + retrieved chunks to an LLM, which answers
                     using only that context (Claude if ANTHROPIC_API_KEY is set,
                     otherwise a local Ollama model — free, no key needed)
```

Each stage of the pipeline lives in its own file under [src/](src/), and
[src/pipeline.py](src/pipeline.py) wires them into two operations: `build_index()`
and `ask()`.

## Tech stack

| Stage | Library |
|---|---|
| PDF parsing | [pypdf](https://pypi.org/project/pypdf/) |
| Chunking | hand-rolled sliding window ([src/chunker.py](src/chunker.py)) |
| Embeddings | [sentence-transformers](https://www.sbert.net/) (`all-MiniLM-L6-v2`, runs locally, no API cost) |
| Vector store | [Chroma](https://www.trychroma.com/) (local, persistent, zero setup) |
| Generation | [Claude](https://www.anthropic.com/) via the `anthropic` SDK, with a free local fallback to [Ollama](https://ollama.com) when no API key is set |

## Setup

```powershell
# 1. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r requirements.txt

# 3. Choose how generation will run — pick ONE:
copy .env.example .env
#   a) Claude (best quality, costs a fraction of a cent per question):
#      edit .env and paste your ANTHROPIC_API_KEY
#   b) Ollama (free, local, no key): install from https://ollama.com, then
#      ollama pull qwen2.5:1.5b   (use a bigger variant if you have more VRAM)
#      Leave ANTHROPIC_API_KEY unset/blank in .env — the app falls back automatically.

# 4. Drop a textbook PDF into data/
```

## Usage

```powershell
# Build the vector index from every PDF in data/
python main.py index

# Ask a single question
python main.py ask "What is the difference between supervised and unsupervised learning?"

# Or chat interactively
python main.py chat
```

## Project structure

```
rag1/
├── data/               # put textbook PDFs here (gitignored)
├── storage/            # persistent Chroma DB, created on first `index` run (gitignored)
├── src/
│   ├── config.py       # all tunables in one place (chunk size, top-k, model names)
│   ├── ingest.py        # step 1 — load PDFs, extract text per page
│   ├── chunker.py        # step 2 — split pages into overlapping chunks
│   ├── embedder.py       # step 3 — text chunks -> vectors
│   ├── vector_store.py   # step 4 — persist/query vectors in Chroma
│   ├── retriever.py      # step 5 — question -> top-k relevant chunks
│   ├── generator.py      # step 6 — chunks + question -> grounded answer (Claude, or Ollama fallback)
│   └── pipeline.py       # orchestrates the steps above
├── main.py              # CLI (index / ask / chat)
└── requirements.txt
```

## Design notes

- **Chunking with overlap** (`CHUNK_SIZE=800`, `CHUNK_OVERLAP=150` in [src/config.py](src/config.py))
  prevents an answer from being split across a chunk boundary with neither half
  having enough context.
- **Local embeddings** keep the indexing step free and offline; only the final
  generation call uses the Claude API, which keeps API usage — and cost — low.
- **Citations**: page and source filename are carried as metadata all the way from
  ingestion through retrieval, so every answer can point back to where it came from.
- **Grounding**: the system prompt instructs the model to answer only from the supplied
  context and say "I don't know" rather than hallucinate when the answer isn't there.
- **Generation fallback**: [src/generator.py](src/generator.py) uses Claude when
  `ANTHROPIC_API_KEY` is set, and otherwise calls a local Ollama model
  (`config.OLLAMA_MODEL`, default `qwen2.5:1.5b` — small enough for GPUs with
  limited VRAM) over its local HTTP API — no key, no cost, no internet required,
  at the price of lower answer quality and depending on local hardware for speed.

## Possible extensions

- Hybrid search (BM25 keyword + vector) for queries with exact terms/numbers.
- Re-ranking retrieved chunks with a cross-encoder before generation.
- A small evaluation set of Q&A pairs to measure retrieval/answer quality.
- A simple web UI (Streamlit/Gradio) instead of the CLI.
