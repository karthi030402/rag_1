"""CLI entry point for the textbook RAG system.

Usage:
    python main.py index              # build the vector index from data/*.pdf
    python main.py ask "question"     # ask a single question
    python main.py chat               # interactive Q&A loop
    python main.py evaluate           # score retrieval + generation against the golden set
"""

import argparse

from src.pipeline import ask, build_index


def cmd_index(_args) -> None:
    print("Building index from PDFs in data/ ...")
    n_chunks = build_index()
    print(f"Done. Indexed {n_chunks} chunks.")


def _print_result(result: dict) -> None:
    print("\nAnswer:\n" + result["answer"])
    print("\nSources:")
    for c in result["sources"]:
        print(f"  - {c['source']}, page {c['page']} (distance={c['distance']:.3f})")


def cmd_ask(args) -> None:
    _print_result(ask(args.question))


def cmd_evaluate(_args) -> None:
    from src.evaluator import run_evaluation

    print("Running evaluation against the golden set...\n")
    report = run_evaluation()

    r = report["retrieval"]
    print(
        f"Retrieval — by page:    Hit Rate: {r['page_hit_rate']:.2%}   MRR: {r['page_mrr']:.3f}\n"
        f"           by content: Hit Rate: {r['content_hit_rate']:.2%}   MRR: {r['content_mrr']:.3f}"
    )
    for q in r["per_question"]:
        page_status = f"HIT (rank {q['page_rank']})" if q["page_hit"] else "MISS"
        content_status = f"HIT (rank {q['content_rank']})" if q["content_hit"] else "MISS"
        print(
            f"  page:[{page_status}] content:[{content_status}] \"{q['question']}\" "
            f"— expected p.{q['expected_page']}, got {q['retrieved_pages']}"
        )

    g = report["generation"]
    print(f"\nGeneration — Answer accuracy: {g['answer_accuracy']:.2%}")
    for q in g["per_question"]:
        status = "PASS" if q["passed"] else "FAIL"
        print(f"  [{status}] \"{q['question']}\" — matched {q['matched_keywords']} of {q['expected_keywords']}")


def cmd_chat(_args) -> None:
    print("Textbook Q&A chat. Type 'exit' to quit.\n")
    while True:
        question = input("You: ").strip()
        if question.lower() in ("exit", "quit"):
            break
        if not question:
            continue
        result = ask(question)
        pages = ", ".join(f"p.{c['page']}" for c in result["sources"])
        print(f"\nAssistant: {result['answer']}\n(sources: {pages})\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="RAG system for textbook Q&A")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("index", help="Build the vector index from PDFs in data/").set_defaults(
        func=cmd_index
    )

    ask_parser = subparsers.add_parser("ask", help="Ask a single question")
    ask_parser.add_argument("question", type=str)
    ask_parser.set_defaults(func=cmd_ask)

    subparsers.add_parser("chat", help="Interactive Q&A loop").set_defaults(func=cmd_chat)

    subparsers.add_parser(
        "evaluate", help="Score retrieval + generation against the golden set"
    ).set_defaults(func=cmd_evaluate)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
