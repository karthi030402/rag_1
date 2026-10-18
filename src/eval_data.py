"""Hand-labeled golden set for evaluation.

Each expected_page was verified by grepping the book's extracted text for the
sentence that actually defines the concept — not guessed from chapter numbers.

expected_phrase is that same verified defining sentence (or a distinctive
fragment of it), used to check retrieval by CONTENT rather than by page number
alone. Page-number matching is a convenient proxy, not the ground truth itself:
a definition can straddle a page boundary, or a page can be split into several
chunks where only one happens to contain the actual sentence — expected_phrase
catches "the right content was retrieved" even when the page number looks wrong.

expected_keywords are terms a correct, grounded LLM answer should mention —
used to score generation quality, separately from retrieval.

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
        "expected_keywords": ["name", "value"],
    },
    {
        "question": "What is a function in Python?",
        "expected_page": 39,
        "expected_source": BOOK,
        "expected_phrase": "named sequence of statements",
        "expected_keywords": ["sequence", "statements"],
    },
    {
        "question": "What is recursion?",
        "expected_page": 65,
        "expected_source": BOOK,
        "expected_phrase": "calls itself",
        "expected_keywords": ["calls itself"],
    },
    {
        "question": "What does a for loop do in Python?",
        "expected_page": 52,
        "expected_source": BOOK,
        "expected_phrase": "for i in range",
        "expected_keywords": ["repeat"],
    },
    {
        "question": "What does a while loop do in Python?",
        "expected_page": 86,
        "expected_source": BOOK,
        "expected_phrase": "while n > 0",
        "expected_keywords": ["repeat"],
    },
    {
        "question": "What is a string in Python?",
        "expected_page": 93,
        "expected_source": BOOK,
        "expected_phrase": "a string is a sequence of characters",
        "expected_keywords": ["sequence", "characters"],
    },
    {
        "question": "What is a list in Python?",
        "expected_page": 111,
        "expected_source": BOOK,
        "expected_phrase": "a list is a sequence of values",
        "expected_keywords": ["sequence", "values"],
    },
    {
        "question": "What is a tuple in Python?",
        "expected_page": 137,
        "expected_source": BOOK,
        "expected_phrase": "a tuple is a sequence of values",
        "expected_keywords": ["sequence", "values"],
    },
    {
        "question": "What is a dictionary in Python?",
        "expected_page": 125,
        "expected_source": BOOK,
        "expected_phrase": "a dictionary is like a list",
        "expected_keywords": ["list"],
    },
]
