"""HTTP API for the textbook RAG system, so clients like the SwiftUI app can ask questions.

Run (either works — both start the same server):
    python api.py                                  # host/port from API_HOST / API_PORT
    uvicorn api:app --host 0.0.0.0 --port 8000

Interactive docs at http://localhost:8000/docs
"""

import logging
import time
from typing import List

import requests
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field

from src import config
from src.generator import GenerationError
from src.pipeline import ask
from src.retriever import IndexNotBuiltError

# uvicorn configures this logger, so messages show up in the server's terminal.
logger = logging.getLogger("uvicorn.error")

app = FastAPI(title="Textbook RAG API")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log every request's final HTTP status and how long it took."""
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "%s %s -> HTTP %d (%.0f ms)",
        request.method, request.url.path, response.status_code, elapsed_ms,
    )
    return response


def require_token(authorization: str = Header(default="")) -> None:
    """If API_TOKEN is set, require `Authorization: Bearer <token>`; otherwise stay open (local dev)."""
    if config.API_TOKEN and authorization != f"Bearer {config.API_TOKEN}":
        raise HTTPException(status_code=401, detail="Missing or invalid API token.")


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1)


class Source(BaseModel):
    text: str
    source: str
    page: int
    distance: float
    similarity: float = Field(..., description="Cosine similarity to the question, 0–100 (%)")


class AskResponse(BaseModel):
    answer: str
    sources: List[Source]


@app.get("/health")
def health() -> dict:
    """Checks the server is up and the configured generation backend is actually usable.

    Any response at all proves uvicorn + FastAPI are running. For Ollama it also
    confirms the server is reachable and the configured model has been pulled;
    for Claude it only reports the configured model (validating the key would
    cost an API call on every health check).
    """
    if config.ANTHROPIC_API_KEY:
        return {"status": "ok", "backend": "claude", "model": config.GENERATION_MODEL}

    try:
        r = requests.get(f"{config.OLLAMA_BASE_URL}/api/tags", timeout=2)
        r.raise_for_status()
        pulled = {m["name"] for m in r.json().get("models", [])}
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=503, detail=f"Ollama is not reachable at {config.OLLAMA_BASE_URL}."
        ) from e

    if config.OLLAMA_MODEL not in pulled:
        raise HTTPException(
            status_code=503,
            detail=f"Model '{config.OLLAMA_MODEL}' is not pulled. Run: ollama pull {config.OLLAMA_MODEL}",
        )
    return {"status": "ok", "backend": "ollama", "model": config.OLLAMA_MODEL}


# Plain `def` (not async): ask() blocks on embedding + LLM calls, so FastAPI
# runs it in a worker thread instead of stalling the event loop.
@app.post("/ask", response_model=AskResponse, dependencies=[Depends(require_token)])
def ask_endpoint(req: AskRequest) -> AskResponse:
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=422, detail="Question must not be blank.")
    try:
        response = AskResponse(**ask(question))
    except IndexNotBuiltError as e:
        logger.warning("/ask failed (503) for %r: %s", question, e)
        raise HTTPException(status_code=503, detail=str(e)) from e
    except GenerationError as e:
        logger.warning("/ask failed (%d) for %r: %s", e.status_code, question, e)
        raise HTTPException(status_code=e.status_code, detail=str(e)) from e

    if config.DEBUG_LOG:
        _log_answer(question, response)
    return response


def _log_answer(question: str, response: AskResponse) -> None:
    """Print the question, answer, sources and the exact JSON body about to be sent."""
    sources = "\n".join(
        f"  {i}. {s.source} p.{s.page} ({s.similarity:.1f}% match, distance {s.distance:.3f})  "
        f"\"{' '.join(s.text.split())[:80]}...\""
        for i, s in enumerate(response.sources, start=1)
    )
    logger.info(
        "\n========== /ask ==========\n"
        "Question: %s\n\n"
        "Answer:\n%s\n\n"
        "Sources:\n%s\n\n"
        "Response JSON:\n%s\n"
        "==========================",
        question, response.answer, sources, response.model_dump_json(indent=2),
    )


if __name__ == "__main__":
    # Only runs for `python api.py`; when uvicorn imports this module, __name__ is "api".
    import uvicorn

    uvicorn.run("api:app", host=config.API_HOST, port=config.API_PORT)
