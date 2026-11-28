"""Step 6: Generation. Ground an LLM's answer in the retrieved chunks.

Uses the Claude API when ANTHROPIC_API_KEY is set. Otherwise falls back to a
local Ollama model (config.OLLAMA_MODEL) — free, no key, no internet required,
but Ollama must be installed and running with that model pulled.
"""

from typing import Dict, List

import anthropic
import requests

from src import config


class GenerationError(RuntimeError):
    """A generation backend failed; carries a user-facing message and an HTTP status for the API."""

    def __init__(self, message: str, status_code: int = 503):
        super().__init__(message)
        self.status_code = status_code


SYSTEM_PROMPT = (
    "You are a study assistant. You answer questions using ONLY the numbered "
    "excerpts from textbooks that you are given.\n"
    "Rules:\n"
    "1. Use only facts stated in the excerpts. Do not add knowledge from "
    "elsewhere, even if you know it.\n"
    "2. For definitions, use the book's own wording. Quote the defining "
    "sentence when there is one.\n"
    "3. After each sentence, cite the excerpt(s) it came from as [1], [2], etc. "
    "Cite only excerpts you actually used.\n"
    "4. If the excerpts do not contain the answer, reply exactly: "
    "\"I couldn't find this in the books.\"\n"
    "5. Be concise: 2-5 sentences, plus a short code example from the excerpts "
    "if it helps."
)


def build_prompt(question: str, context_chunks: List[Dict]) -> str:
    # Numbers match the order of `sources` in the API response:
    # [1] = sources[0], [2] = sources[1], ...
    excerpts = "\n\n".join(
        f"[{i}] {c['source']}, page {c['page']}\n{c['text']}"
        for i, c in enumerate(context_chunks, start=1)
    )
    # Small models follow the instruction nearest the end best, so repeat
    # the key rules after the question.
    return (
        f"Excerpts:\n{excerpts}\n\n"
        f"Question: {question}\n\n"
        "Answer using only the excerpts above, in the book's wording, "
        "citing excerpts as [n]."
    )


def _generate_with_claude(prompt: str) -> str:
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    try:
        response = client.messages.create(
            model=config.GENERATION_MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
    except anthropic.AuthenticationError as e:
        raise GenerationError("Anthropic rejected the API key. Check ANTHROPIC_API_KEY.", 502) from e
    except anthropic.NotFoundError as e:
        raise GenerationError(
            f"Claude model '{config.GENERATION_MODEL}' not found. Check CLAUDE_MODEL.", 502
        ) from e
    except anthropic.RateLimitError as e:
        raise GenerationError("Claude rate limit reached. Try again shortly.", 429) from e
    except anthropic.APIConnectionError as e:
        raise GenerationError("Could not reach the Anthropic API.", 503) from e
    except anthropic.APIStatusError as e:
        raise GenerationError(f"Claude API error ({e.status_code}).", 502) from e
    return response.content[0].text


def _generate_with_ollama(prompt: str) -> str:
    try:
        response = requests.post(
            f"{config.OLLAMA_BASE_URL}/api/generate",
            json={
                "model": config.OLLAMA_MODEL,
                "system": SYSTEM_PROMPT,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": config.OLLAMA_TEMPERATURE,
                    "seed": config.OLLAMA_SEED,
                },
            },
            timeout=300,
        )
        response.raise_for_status()
    except requests.exceptions.ConnectionError as e:
        raise GenerationError(
            f"Could not reach Ollama at {config.OLLAMA_BASE_URL}. "
            "Is it installed and running? (Install from https://ollama.com, "
            f"then run `ollama pull {config.OLLAMA_MODEL}`.)"
        ) from e
    except requests.exceptions.Timeout as e:
        raise GenerationError("Ollama took too long to answer.", 504) from e
    except requests.exceptions.HTTPError as e:
        if response.status_code == 404:
            raise GenerationError(
                f"Ollama model '{config.OLLAMA_MODEL}' is not pulled. "
                f"Run: ollama pull {config.OLLAMA_MODEL}"
            ) from e
        raise GenerationError(f"Ollama returned HTTP {response.status_code}.", 502) from e
    try:
        return response.json()["response"]
    except (ValueError, KeyError) as e:
        raise GenerationError("Ollama returned an unexpected response.", 502) from e


def generate_answer(question: str, context_chunks: List[Dict]) -> str:
    prompt = build_prompt(question, context_chunks)

    if config.ANTHROPIC_API_KEY:
        return _generate_with_claude(prompt)

    print(f"[info] No ANTHROPIC_API_KEY set — using local Ollama model '{config.OLLAMA_MODEL}'.")
    return _generate_with_ollama(prompt)
