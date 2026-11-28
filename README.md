# Textbook RAG — Retrieval-Augmented Q&A

A Retrieval-Augmented Generation (RAG) system that answers questions about textbooks
(or any PDFs) by retrieving the relevant passages and grounding an LLM's answer in them,
with page-number citations and a similarity score per source. Use it from the CLI, or
over HTTP through a FastAPI server (e.g. from a SwiftUI iOS app).

## How it works

```
PDF textbooks (data/*.pdf)
     │  (src/ingest.py)
     ▼
Raw text per page
     │  (src/chunker.py)
     ▼
Overlapping text chunks  ──────────────┐
     │  (src/embedder.py)              │
     ▼                                 │
Chunk embeddings (unit length)         │  metadata: source file + page number
     │  (src/vector_store.py)          │  carried through every step, so the
     ▼                                 │  final answer can cite where it came from
Chroma vector database (cosine) ◄──────┘
     │
     │  question comes in (CLI: main.py  ·  HTTP: api.py → POST /ask)
     ▼
src/retriever.py  → embeds the question, finds top-k nearest chunks,
                     converts each distance into a % similarity
     │
     ▼
src/generator.py  → sends question + retrieved chunks to an LLM, which answers
                     using only that context (Claude if ANTHROPIC_API_KEY is set,
                     otherwise a local Ollama model — free, no key needed)
```

Each stage of the pipeline lives in its own file under [src/](src/), and
[src/pipeline.py](src/pipeline.py) wires them into three operations: `build_index()`
(full rebuild), `add_book()` (index one new PDF) and `ask()`.

## Tech stack

| Stage | Library |
|---|---|
| PDF parsing | [pypdfium2](https://pypi.org/project/pypdfium2/) (PDFium, Chrome's PDF engine; keeps word spacing at font changes) |
| Chunking | hand-rolled sentence packing ([src/chunker.py](src/chunker.py)) |
| Embeddings | [sentence-transformers](https://www.sbert.net/) (`BAAI/bge-small-en-v1.5`, runs locally, no API cost) |
| Vector store | [Chroma](https://www.trychroma.com/) (local, persistent, cosine distance) |
| Generation | [Claude](https://www.anthropic.com/) via the `anthropic` SDK, with a free local fallback to [Ollama](https://ollama.com) when no API key is set |
| HTTP API | [FastAPI](https://fastapi.tiangolo.com/) + [uvicorn](https://www.uvicorn.org/) ([api.py](api.py)) |

## Setup

Requires **Python 3.10+** (`requests` in requirements.txt needs it).

```bash
# 1. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate          # macOS / Linux
# .venv\Scripts\Activate.ps1       # Windows PowerShell

# 2. Install dependencies
pip install -r requirements.txt

# 3. Choose how generation will run — pick ONE:
cp .env.example .env               # Windows: copy .env.example .env
#   a) Claude (best quality, costs a fraction of a cent per question):
#      edit .env and paste your ANTHROPIC_API_KEY
#   b) Ollama (free, local, no key): install the app from https://ollama.com
#      (it runs in the background on http://localhost:11434), then
#      ollama pull qwen2.5:1.5b   (use a bigger variant if you have more RAM/VRAM)
#      Leave ANTHROPIC_API_KEY="" in .env — the app falls back automatically.

# 4. Put one or more textbook PDFs into data/ (see "Books" below)
```

## Books

Any text-based PDF works. The project is set up with these free books
(Allen B. Downey, Green Tea Press, Creative Commons licensed):

| Book | File in `data/` | Download |
|---|---|---|
| Think Python 2e (used by the evaluation golden set) | `thinkpython2.pdf` | https://greenteapress.com/thinkpython2/thinkpython2.pdf |
| Think Stats 2e | `thinkstats2.pdf` | https://greenteapress.com/thinkstats2/thinkstats2.pdf |

More books in the same style, if you want to extend the library:
[Think Bayes](https://greenteapress.com/thinkbayes/thinkbayes.pdf),
[Think Complexity 2e](https://greenteapress.com/complexity2/thinkcomplexity2.pdf),
[Think DSP](https://greenteapress.com/thinkdsp/thinkdsp.pdf),
[Think Java 2e](https://greenteapress.com/thinkjava7/thinkjava2.pdf).

```bash
curl -L -o data/thinkbayes.pdf https://greenteapress.com/thinkbayes/thinkbayes.pdf
python main.py add data/thinkbayes.pdf
```

Every answer's sources include the PDF file name, so you can tell which book a
chunk came from.

## Usage

```bash
# Build the vector index from every PDF in data/ (full rebuild)
python main.py index

# Add one new PDF (already copied into data/) without re-embedding the others
python main.py add data/<new-book>.pdf

# Ask a single question
python main.py ask "What is a tuple in Python?"

# Or chat interactively
python main.py chat

# Score retrieval + answer quality against the golden set (see Evaluation below)
python main.py evaluate
```

Example `ask` output:

```
Sources:
  - thinkpython2.pdf, page 137 (65.0% match, distance=0.350)
  - thinkpython2.pdf, page 142 (56.8% match, distance=0.432)
```

### `index` vs `add`

| Situation | Command |
|---|---|
| First time, or new set of PDFs | `python main.py index` |
| Added one new PDF to `data/` | `python main.py add data/<book>.pdf` — only that book is embedded |
| Replaced or removed a PDF | `python main.py index` — `add` can't detect a changed file with the same name |
| Changed `CHUNK_STRATEGY`, `CHUNK_SIZE`, `CHUNK_OVERLAP`, `EMBEDDING_MODEL` or `DISTANCE_METRIC` | `python main.py index` — every vector must be rebuilt |
| Changed the LLM, `TOP_K`, prompts or API code | No re-index needed; just restart the server |

`add` skips a book that's already indexed, and refuses PDFs outside `data/` (so a
later full `index` won't silently drop them). If the API server is running,
restart it after `index` or `add`.

## HTTP API (for apps)

[api.py](api.py) exposes the pipeline over HTTP, e.g. for a SwiftUI iOS app.

```bash
python api.py                                  # host/port from API_HOST / API_PORT
# or
uvicorn api:app --host 0.0.0.0 --port 8000
```

Stop it with `Ctrl+C`. Interactive docs: http://localhost:8000/docs

| Endpoint | Purpose |
|---|---|
| `GET /health` | Server is up **and** the generation backend is usable. For Ollama it checks the server is reachable and `OLLAMA_MODEL` is pulled (503 otherwise). |
| `POST /ask` | `{"question": "..."}` → `{"answer": "...", "sources": [{text, source, page, distance, similarity}]}` |

```bash
curl http://localhost:8000/health

curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is a tuple in Python?"}'

# when API_TOKEN is set in .env:
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your-token>" \
  -d '{"question": "What is a tuple in Python?"}'
```

`similarity` is the cosine similarity between the question and the chunk as a
0–100 percentage; `distance` is Chroma's raw distance (`1 - cosine`).

**Errors** are returned as `{"detail": "..."}` with these status codes:

| Status | When |
|---|---|
| 401 | `API_TOKEN` is set and the `Authorization: Bearer` header is missing or wrong |
| 422 | Missing or blank question |
| 429 | Claude rate limit |
| 502 | Claude auth/model error, or an unexpected Ollama response |
| 503 | Index is empty (run `index`), Ollama not running, or model not pulled |
| 504 | Ollama timed out |

**Server terminal logging:** every request logs `METHOD /path -> HTTP status (ms)`.
With `DEBUG_LOG=true` (the default), each `/ask` also prints the question, answer,
numbered sources with similarity %, and the exact JSON sent back.

**Connecting from iOS:**
- Simulator: `http://localhost:8000` reaches the Mac directly.
- Real iPhone (same Wi-Fi): use the Mac's LAN IP, e.g. `http://<your-mac-ip>:8000`
  (find it with `ipconfig getifaddr en0`).
  The server must listen on `0.0.0.0` (the default `API_HOST`).
- Add `NSAllowsLocalNetworking` (App Transport Security) and
  `NSLocalNetworkUsageDescription` to the app's Info.plist for plain-HTTP local access.

## Configuration

Set in `.env` (see [.env.example](.env.example)); defaults live in [src/config.py](src/config.py).

| Variable | Default | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | `""` | Set to use Claude; empty → Ollama |
| `CLAUDE_MODEL` | `claude-sonnet-5-5` | Claude model ID |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server |
| `OLLAMA_MODEL` | `qwen2.5:1.5b` | Local model (must be pulled) |
| `OLLAMA_TEMPERATURE` / `OLLAMA_SEED` | `0` / `42` | Deterministic answers, so `evaluate` scores are comparable between runs |
| `API_TOKEN` | unset | When set, `/ask` requires `Authorization: Bearer <token>` |
| `API_HOST` / `API_PORT` | `0.0.0.0` / `8000` | Where `python api.py` listens (`127.0.0.1` = this Mac only) |
| `DEBUG_LOG` | `true` | Print each `/ask` in the server terminal |

Code-level settings in [src/config.py](src/config.py): `CHUNK_SIZE=800`,
`CHUNK_OVERLAP=150`, `EMBEDDING_MODEL`, `DISTANCE_METRIC="cosine"`, `TOP_K=4`.

## Evaluation

`python main.py evaluate` runs every question in a hand-labeled golden set
([src/eval_data.py](src/eval_data.py)) through the pipeline and scores the two
halves independently ([src/evaluator.py](src/evaluator.py)):

| What | Metric | How it's checked |
|---|---|---|
| Retrieval, by page | Hit Rate@k, MRR | a top-k chunk has the expected page **and** source PDF |
| Retrieval, by content | Hit Rate@k, MRR | a top-k chunk's text contains the expected defining phrase |
| Generation | Answer accuracy | the answer contains all expected keywords |

Page matching is a cheap proxy; content matching checks what was actually retrieved,
so reporting both shows when chunking or page boundaries mislead the page score.
Generation uses keyword containment rather than an LLM-as-judge, so evaluation
costs nothing beyond the answer calls themselves.

The golden set is written for *Think Python 2nd Edition* only — save it as
`data/thinkpython2.pdf` and run `python main.py index` first. Other books in `data/`
are fine (they don't change the Think Python scores), but their questions aren't
scored yet. To evaluate another book, add entries to
[src/eval_data.py](src/eval_data.py) with your own questions, pages, phrases and keywords.

Every score change is tracked, with its config snapshot and reference Q&A, in
[docs/EVALUATION_LOG.md](docs/EVALUATION_LOG.md). Add an entry there after each change.

Baseline with Ollama `qwen2.5:1.5b` (Think Python, Think Stats and Think Bayes indexed):

| Metric | Result |
|---|---|
| Retrieval by page | Hit Rate 55.6%, MRR 0.472 |
| Retrieval by content | Hit Rate 44.4%, MRR 0.306 |
| Generation | ~67–89% — varies between runs with the small local model |

## Project structure

```
rag_1/
├── data/                 # textbook PDFs (gitignored)
├── storage/              # persistent Chroma DB, created on first `index` run (gitignored)
├── src/
│   ├── config.py         # all tunables in one place (chunking, metric, top-k, models, API)
│   ├── ingest.py         # step 1 — load PDFs, extract text per page
│   ├── chunker.py        # step 2 — split pages into overlapping chunks
│   ├── embedder.py       # step 3 — text chunks -> unit-length vectors
│   ├── vector_store.py   # step 4 — persist/query vectors in Chroma (cosine)
│   ├── retriever.py      # step 5 — question -> top-k chunks with % similarity
│   ├── generator.py      # step 6 — chunks + question -> grounded answer (Claude, or Ollama fallback)
│   ├── pipeline.py       # orchestrates the steps: build_index / add_book / ask
│   ├── evaluator.py      # step 8 — score retrieval + generation against the golden set
│   └── eval_data.py      # hand-labeled golden set (questions, pages, phrases, keywords)
├── api.py                # FastAPI server: GET /health, POST /ask
├── main.py               # CLI (index / add / ask / chat / evaluate)
├── .env.example          # copy to .env
└── requirements.txt
```

## Design notes

- **Sentence chunking with overlap** (`CHUNK_STRATEGY="sentence"`, `CHUNK_SIZE=800`,
  `CHUNK_OVERLAP=150` in [src/config.py](src/config.py)): whole sentences are packed
  into chunks of up to 800 characters, so a chunk never starts or ends mid-sentence,
  and the last sentence(s) of each chunk are repeated at the start of the next.
  Each page is split into roughly equal chunks, and a short final sentence joins
  the previous chunk instead of becoming a tiny chunk of its own. Line breaks are
  kept, so code examples stay readable. Set `CHUNK_STRATEGY=fixed` for the old
  800-character sliding window.
- **Local embeddings** keep the indexing step free and offline; only the final
  generation call uses the Claude API, which keeps API usage — and cost — low.
- **Embedding model**: `BAAI/bge-small-en-v1.5` (switched from `all-MiniLM-L6-v2`;
  same 384 dims, better retrieval quality). Questions are embedded with BGE's query
  instruction prefix (`QUERY_INSTRUCTION` in config); chunks are embedded without it.
- **Page cleanup at ingestion** ([src/ingest.py](src/ingest.py)): title/copyright
  pages (before the PDF's first bookmark), table-of-contents and index pages, and
  each page's running header ("116 Chapter 12. Tuples") are removed before chunking,
  so they can't take retrieval slots. Page numbers are unchanged.
- **Index cleanup**: Chroma's `delete_collection()` leaves the old vector folder on
  disk, so a full `index` also removes any `storage/<uuid>/` folder that
  `chroma.sqlite3` no longer references.
- **Cosine distance**: embeddings are encoded with `normalize_embeddings=True`, so every
  vector has length 1. For unit vectors cosine, squared L2 (`2 − 2·cos`) and inner
  product all rank chunks identically; cosine is used because `distance = 1 − similarity`
  is directly readable and it stays correct even with a model that doesn't normalize.
  The metric is fixed when the collection is created, so changing `DISTANCE_METRIC`
  needs a full `index`. The retriever reads the metric from the collection itself,
  so the % similarity stays correct for an index built with the old default (`l2`).
- **Citations**: page and source filename are carried as metadata all the way from
  ingestion through retrieval, so every answer can point back to where it came from.
- **Grounding**: the system prompt instructs the model to answer only from the supplied
  context and say "I don't know" rather than hallucinate when the answer isn't there.
- **Generation fallback**: [src/generator.py](src/generator.py) uses Claude when
  `ANTHROPIC_API_KEY` is set, and otherwise calls a local Ollama model
  (`config.OLLAMA_MODEL`, default `qwen2.5:1.5b`) over its local HTTP API — no key,
  no cost, no internet required, at the price of lower answer quality.
- **Error mapping**: generator failures raise `GenerationError` with an HTTP status,
  and an empty index raises `IndexNotBuiltError`, so the API returns meaningful
  status codes instead of a generic 500.
- **Sync endpoints**: `/ask` is a plain `def`, so FastAPI runs it in a worker thread
  and the blocking embedding/LLM calls don't stall the event loop.
- **Telemetry pin**: `posthog<6` in requirements.txt — chromadb 0.5.x calls posthog
  with the old `capture()` signature, and posthog 6+ prints errors on every run.

## Changelog

Changes since the original CLI-only version:

- **HTTP API** — new [api.py](api.py) (FastAPI): `GET /health` with real Ollama
  checks, `POST /ask`, optional bearer-token auth (`API_TOKEN`), request/status
  logging, debug logging of each answer, and `python api.py` start-up via `uvicorn.run`.
- **Similarity %** — each source now includes `similarity` (0–100) next to `distance`,
  in the CLI output and the API response.
- **Cosine distance** — collection created with `hnsw:space = DISTANCE_METRIC`
  (`"cosine"`) instead of Chroma's default `l2`.
- **Incremental indexing** — new `python main.py add data/<book>.pdf`
  (`add_book()`, `load_pdf()`, `is_indexed()`).
- **Second book** — Think Stats 2e added alongside Think Python 2e.
- **Error handling** — `GenerationError` (with status codes for Claude and Ollama
  failures) and `IndexNotBuiltError` for an empty index.
- **Config** — `CLAUDE_MODEL` default `claude-sonnet-5-5`, `OLLAMA_MODEL` default
  `qwen2.5:1.5b`, new `DISTANCE_METRIC`, `API_TOKEN`, `API_HOST`, `API_PORT`, `DEBUG_LOG`.
- **Dependencies** — added `fastapi`, `uvicorn`; pinned `posthog<6` to silence
  chromadb telemetry errors.
- **Docs** — evaluation section, macOS setup, API, configuration and books sections.

## Possible extensions

- Hybrid search (BM25 keyword + vector) for queries with exact terms/numbers.
- Re-ranking retrieved chunks with a cross-encoder before generation.
- A larger golden set covering every indexed book, and LLM-as-judge scoring for
  answers that paraphrase the keywords.
- Filter retrieval by book (`where={"source": ...}`) so an app can ask one book at a time.
- Streaming answers to the app, and conversation memory for follow-up questions.
