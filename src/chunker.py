"""Step 2: Chunking. Split page text into overlapping chunks sized for embedding.

Two strategies (config.CHUNK_STRATEGY):
  - "sentence" (default): pack whole sentences into chunks of up to CHUNK_SIZE
    characters. A chunk never starts or ends mid-sentence, so a definition like
    "A function that calls itself is recursive" is never cut in half.
  - "fixed": the original sliding window of CHUNK_SIZE characters. Kept so the
    two can be compared in the evaluation log.
"""

import math
import re
from typing import Dict, List, Tuple

from src import config

# A sentence ends at . ! or ? (optionally followed by a closing quote or bracket),
# then whitespace, then something that can start a sentence: a capital letter,
# an opening quote/bracket, or a ">>>" interpreter prompt. Requiring the capital
# avoids splitting "e.g. a list", "i.e. the" and URLs like "thinkpython. com".
_SENTENCE_END = re.compile(r"(?<=[.!?])([”\"')\]]?)\s+(?=[A-Z“\"(\[•]|>>>)")
# A page's final sentence shorter than this is folded into the previous chunk
# (which may then exceed CHUNK_SIZE by up to this much) instead of standing alone.
MIN_TAIL_CHARS = 200
# The last sentence of a chunk is always repeated in the next one if it is at
# most this many times CHUNK_OVERLAP, even when it is longer than the overlap.
MAX_CARRY_FACTOR = 2


def _sentence_spans(text: str) -> List[Tuple[int, int]]:
    """(start, end) offsets of each sentence in text. Chunks are later cut from
    the original text by these offsets, so line breaks (code!) are kept as-is."""
    spans, start = [], 0
    for match in _SENTENCE_END.finditer(text):
        end = match.start() + len(match.group(1))  # keep a closing quote/bracket with its sentence
        spans.append((start, end))
        start = match.end()
    spans.append((start, len(text)))
    return [(s, e) for s, e in spans if text[s:e].strip()]


def _window_spans(start: int, end: int, size: int, overlap: int) -> List[Tuple[int, int]]:
    """Fixed-size character windows over text[start:end]."""
    spans = []
    while start < end:
        spans.append((start, min(start + size, end)))
        if start + size >= end:
            break
        start += size - overlap
    return spans


def _window_split(text: str, size: int, overlap: int) -> List[str]:
    """The "fixed" strategy: a sliding window of `size` characters."""
    pieces = (text[s:e].strip() for s, e in _window_spans(0, len(text), size, overlap))
    return [p for p in pieces if p]


def _pack_sentences(text: str, size: int, overlap: int) -> List[str]:
    """Greedily pack whole sentences into chunks, repeating the last sentence(s) of
    each chunk (up to `overlap` characters) at the start of the next one.

    The page is split into equal-ish chunks rather than "full, full, leftover":
    a 1,000-character page becomes two ~500-character chunks, not 800 + 200,
    so no chunk is a short scrap with too little context to embed well.
    A single sentence longer than `size` (e.g. a long code listing with no full
    stop) falls back to fixed windows.
    """
    if len(text) <= size:
        return [text.strip()]
    units: List[Tuple[int, int]] = []
    for s, e in _sentence_spans(text):
        units.extend([(s, e)] if e - s <= size else _window_spans(s, e, size, overlap))

    # Each chunk after the first repeats up to `overlap` characters, so it adds
    # about (size - overlap) new ones. Spread the page's text evenly over that
    # many chunks; `target` is how much NEW text each chunk should take.
    target = len(text) / math.ceil((len(text) - overlap) / (size - overlap))
    groups: List[List[Tuple[int, int]]] = []
    current: List[Tuple[int, int]] = []
    new_from = 0  # offset where the current chunk's new (not repeated) text starts
    for unit in units:
        if current and (unit[1] - current[0][0] > size or current[-1][1] - new_from >= target):
            groups.append(current)
            # Overlap: carry trailing sentences that fit in `overlap` characters.
            # Textbook sentences are often longer than that budget (a quarter are
            # over 150 chars), so always carry at least the last sentence unless
            # it exceeds MAX_CARRY_FACTOR × overlap; otherwise ~40% of chunks
            # would start with no context at all.
            carried = [u for u in current if current[-1][1] - u[0] <= overlap]
            if not carried and current[-1][1] - current[-1][0] <= MAX_CARRY_FACTOR * overlap:
                carried = current[-1:]
            # Never carry so much that the new sentence would overflow the chunk.
            carried = [u for u in carried if unit[1] - u[0] <= size]
            current = carried
            new_from = unit[0]
        current.append(unit)
    tail = [u for u in current if u[0] >= new_from]
    if groups and tail[-1][1] - new_from < MIN_TAIL_CHARS and tail[-1][1] - groups[-1][0][0] <= size + MIN_TAIL_CHARS:
        # The page's last sentence didn't fit the previous chunk; rather than
        # leave it as a tiny chunk of its own, let that chunk run slightly long.
        groups[-1].extend(tail)
    else:
        groups.append(current)
    return [text[g[0][0]:g[-1][1]].strip() for g in groups]


def chunk_pages(pages: List[Dict]) -> List[Dict]:
    """Split each page into chunks, carrying source/page metadata so every
    retrieved chunk can still be cited. Chunks stay within one page, so a
    chunk's page number is always exact.
    """
    split = _pack_sentences if config.CHUNK_STRATEGY == "sentence" else _window_split
    chunks: List[Dict] = []
    for page in pages:
        for text in split(page["text"], config.CHUNK_SIZE, config.CHUNK_OVERLAP):
            chunks.append({"text": text, "source": page["source"], "page": page["page"]})
    return chunks
