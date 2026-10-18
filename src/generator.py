"""Step 6: Generation. Ground an LLM's answer in the retrieved chunks.

Uses the Claude API when ANTHROPIC_API_KEY is set. Otherwise falls back to a
local Ollama model (config.OLLAMA_MODEL) — free, no key, no internet required,
but Ollama must be installed and running with that model pulled.
"""

from typing import Dict, List

import anthropic
import requests

from src import config

SYSTEM_PROMPT = (
    "You are a study assistant answering questions about a specific textbook. "
    "Answer ONLY using the provided context. If the answer is not contained in "
    "the context, say you don't know instead of guessing. When you use a piece "
    "of context, cite its page like (p. 12)."
)


def build_prompt(question: str, context_chunks: List[Dict]) -> str:
    context_block = "\n\n".join(
        f"[Page {c['page']} of {c['source']}]\n{c['text']}" for c in context_chunks
    )
    return f"Context:\n{context_block}\n\nQuestion: {question}"


def _generate_with_claude(prompt: str) -> str:
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=config.GENERATION_MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
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
            },
            timeout=300,
        )
        response.raise_for_status()
    except requests.exceptions.ConnectionError as e:
        raise RuntimeError(
            f"Could not reach Ollama at {config.OLLAMA_BASE_URL}. "
            "Is it installed and running? (Install from https://ollama.com, "
            f"then run `ollama pull {config.OLLAMA_MODEL}`.)"
        ) from e
    return response.json()["response"]


def generate_answer(question: str, context_chunks: List[Dict]) -> str:
    prompt = build_prompt(question, context_chunks)

    if config.ANTHROPIC_API_KEY:
        return _generate_with_claude(prompt)

    print(f"[info] No ANTHROPIC_API_KEY set — using local Ollama model '{config.OLLAMA_MODEL}'.")
    return _generate_with_ollama(prompt)
