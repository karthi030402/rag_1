"""Step 8: Evaluation. Measure retrieval accuracy and answer quality against a
hand-labeled golden set (src/eval_data.py), independently of each other.

Retrieval is scored two ways, on purpose:
  - by PAGE + SOURCE (Hit Rate@k, MRR) — cheap and exact, but only a proxy: a
    chunk can share the "right" page number without containing the actual
    defining sentence, since chunking can split one page into pieces where
    only one piece has the relevant text; conversely a definition can spill
    onto the next physical page, making a "wrong" page number actually
    correct content. Source is checked alongside page because page numbers
    are only unique within one book — with multiple PDFs in data/, two books
    can both have a "page 31," and checking page alone would count a match
    against the wrong book as a hit.
  - by CONTENT (expected_phrase found in the retrieved chunk's real text) —
    more expensive to prepare (needs a verified phrase per question) but
    immune to that page-boundary/chunking artifact, since it checks what was
    actually retrieved rather than a metadata label.
Reporting both, side by side, is what surfaces the gap between them.

Generation is scored with a simple keyword-containment check rather than an
LLM-as-judge, to keep evaluation free and fast (no extra API/model calls
beyond the ones already being tested).
"""

from typing import Dict, List

from src.eval_data import GOLDEN_SET
from src.pipeline import ask
from src.retriever import retrieve

def _first_rank_matching(items_in_rank_order: List, predicate) -> "int | None":
    for i, item in enumerate(items_in_rank_order, start=1):
        if predicate(item):
            return i
    return None


def evaluate_retrieval(golden_set: List[Dict] = GOLDEN_SET) -> Dict:
    page_hits = 0
    page_reciprocal_ranks = []
    content_hits = 0
    content_reciprocal_ranks = []
    per_question = []

    for item in golden_set:
        chunks = retrieve(item["question"])
        pages = [c["page"] for c in chunks]

        page_rank = _first_rank_matching(
            chunks,
            lambda c: c["page"] == item["expected_page"] and c["source"] == item["expected_source"],
        )
        page_hit = page_rank is not None
        page_hits += page_hit
        page_reciprocal_ranks.append(1 / page_rank if page_hit else 0)

        phrase = item["expected_phrase"].lower()
        content_rank = _first_rank_matching(chunks, lambda c: phrase in c["text"].lower())
        content_hit = content_rank is not None
        content_hits += content_hit
        content_reciprocal_ranks.append(1 / content_rank if content_hit else 0)

        per_question.append({
            "question": item["question"],
            "expected_page": item["expected_page"],
            "retrieved_pages": pages,
            "page_hit": page_hit,
            "page_rank": page_rank,
            "content_hit": content_hit,
            "content_rank": content_rank,
        })

    n = len(golden_set)
    return {
        "page_hit_rate": page_hits / n,
        "page_mrr": sum(page_reciprocal_ranks) / n,
        "content_hit_rate": content_hits / n,
        "content_mrr": sum(content_reciprocal_ranks) / n,
        "per_question": per_question,
    }


def evaluate_generation(golden_set: List[Dict] = GOLDEN_SET) -> Dict:
    correct = 0
    per_question = []

    for item in golden_set:
        result = ask(item["question"])
        answer_lower = result["answer"].lower()
        matched = [kw for kw in item["expected_keywords"] if kw.lower() in answer_lower]
        passed = len(matched) == len(item["expected_keywords"])
        correct += passed
        per_question.append({
            "question": item["question"],
            "answer": result["answer"],
            "expected_keywords": item["expected_keywords"],
            "matched_keywords": matched,
            "passed": passed,
        })

    n = len(golden_set)
    return {
        "answer_accuracy": correct / n,
        "per_question": per_question,
    }


def run_evaluation() -> Dict:
    return {
        "retrieval": evaluate_retrieval(),
        "generation": evaluate_generation(),
    }
