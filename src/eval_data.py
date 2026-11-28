"""Hand-labeled golden set for evaluation.

Each expected_page was verified by grepping the book's extracted text for the
sentence that actually defines the concept — not guessed from chapter numbers.

expected_phrase is that same verified defining sentence (or a distinctive
fragment of it), used to check retrieval by CONTENT rather than by page number
alone. Page-number matching is a convenient proxy, not the ground truth itself:
a definition can straddle a page boundary, or a page can be split into several
chunks where only one happens to contain the actual sentence — expected_phrase
catches "the right content was retrieved" even when the page number looks wrong.
Phrases are the book's exact wording (matched case- and whitespace-insensitively).

expected_keywords are terms a correct, grounded LLM answer should mention —
used to score generation quality, separately from retrieval.
Each entry is a GROUP of accepted alternatives: the answer must match every
group, and any one alternative in a group counts ("sequence" OR "ordered
collection"). Alternatives come from the book's own wording (e.g. it calls
list values "elements or sometimes items"), not from model answers.
A plain string is a group with one alternative.

expected_source pins which PDF the expected_page number belongs to. Page
numbers are only unique WITHIN one book — if data/ ever holds more than one
PDF, two different books can both have a "page 31," and a page-only check
would count a match against the wrong book as a hit. Checking source alongside
page is what rules that out.
"""

BOOK = "thinkpython2.pdf"

GOLDEN_SET = [
    {
        "question": "What is a variable in Python?",
        "expected_page": 31,
        "expected_source": BOOK,
        "expected_phrase": "a variable is a name that refers to a value",
        "expected_keywords": [["name"], ["value"]],
    },
    {
        "question": "What is a function in Python?",
        "expected_page": 39,
        "expected_source": BOOK,
        "expected_phrase": "named sequence of statements",
        "expected_keywords": [["sequence", "series"], ["statements"]],
    },
    {
        "question": "What is recursion?",
        "expected_page": 65,
        "expected_source": BOOK,
        # The book's definition sentence; "calls itself" alone also matches the
        # countdown walkthrough on pp.65-66 and p.162.
        "expected_phrase": "a function that calls itself is recursive",
        "expected_keywords": [["calls itself", "call itself", "calling itself"]],
    },
    {
        "question": "What does a for loop do in Python?",
        # p.52 only introduces section 4.2; the definition is on p.53.
        # (The old phrase "for i in range" was code found in 28 chunks across 3 books.)
        "expected_page": 53,
        "expected_source": BOOK,
        "expected_phrase": "a for statement is also called a loop",
        "expected_keywords": [["repeat", "loops back", "each", "every", "again"]],
    },
    {
        "question": "What does a while loop do in Python?",
        # The old phrase "while n > 0" was on p.87 while expected_page said 86.
        "expected_page": 87,
        "expected_source": BOOK,
        "expected_phrase": "flow of execution for a while statement",
        "expected_keywords": [
            ["condition"],
            ["repeat", "as long as", "until", "go back", "loops back"],
        ],
    },
    {
        "question": "What is a string in Python?",
        "expected_page": 93,
        "expected_source": BOOK,
        "expected_phrase": "a string is a sequence of characters",
        "expected_keywords": [["sequence", "ordered collection"], ["characters"]],
    },
    {
        "question": "What is a list in Python?",
        "expected_page": 111,
        "expected_source": BOOK,
        "expected_phrase": "a list is a sequence of values",
        # Book: "The values in a list are called elements or sometimes items."
        "expected_keywords": [
            ["sequence", "ordered collection"],
            ["values", "elements", "items"],
        ],
    },
    {
        "question": "What is a tuple in Python?",
        "expected_page": 137,
        "expected_source": BOOK,
        "expected_phrase": "a tuple is a sequence of values",
        # Book glossary: "An immutable sequence of elements"; immutability is
        # "the important difference" from lists, so a definition must say it.
        "expected_keywords": [
            ["sequence", "ordered collection"],
            ["values", "elements"],
            ["immutable"],
        ],
    },
    {
        "question": "What is a dictionary in Python?",
        "expected_page": 125,
        "expected_source": BOOK,
        "expected_phrase": "a dictionary is like a list",
        # Book: "a collection of indices, which are called keys, and a collection of values"
        "expected_keywords": [["key"], ["value"]],
    },
]
