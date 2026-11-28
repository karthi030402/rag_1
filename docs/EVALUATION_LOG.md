# Evaluation Log

A running record of how the RAG pipeline scores over time. Each entry gives a
snapshot of the configuration, the `python main.py evaluate` output, and answers
to a fixed set of **reference questions**. After any change, re-run the same
commands and add a new entry at the top so the scores can be compared directly.

## How to add an entry

```bash
python main.py evaluate
python main.py ask "What is a tuple in Python?"      # reference Q1: retrieval hit
python main.py ask "What is recursion?"              # reference Q2: retrieval miss
```

1. Copy the **Entry template** at the bottom and fill it in.
2. Update the **Config snapshot**. Anything that changed since the last entry is
   the likely cause of a score change.
3. Answers from the local model vary between runs. If generation accuracy moves
   by only one question, re-run before drawing conclusions.
4. Changing chunking, the embedding model or the distance metric needs
   `python main.py index` before evaluating.

## Scoreboard

| # | Date | Commit | Change | Page HR | Page MRR | Content HR | Content MRR | Answer acc. |
|---|---|---|---|---|---|---|---|---|
| 8 | 2026-11-27 | `865bb38` + uncommitted | Sentence chunking (800/150) | 88.89% | 0.639 | 88.89% | 0.694 | 88.89% |
| 7 | 2026-11-27 | `865bb38` + uncommitted | Page cleanup at ingestion (TOC/index/front matter/running headers) | 88.89% | 0.759 | 88.89% | 0.759 | 100.00% |
| 6 | 2026-11-26 | `865bb38` + uncommitted | Prompt: numbered excerpts, citations, book wording | 88.89% | 0.833 | 88.89% | 0.833 | **100.00%** (citations in 1/9) |
| 5 | 2026-11-26 | `865bb38` + uncommitted | Golden set fixes + keyword synonym groups ⚠️ new scoring | 88.89% | 0.833 | 88.89% | 0.833 | 88.89% |
| 4 | 2026-11-26 | `865bb38` + uncommitted | PDF extraction pypdf → `pypdfium2` | **88.89%** | **0.778** | **88.89%** | **0.833** | 55.56% (deterministic) |
| 3 | 2026-11-25 | `865bb38` + uncommitted | Ollama `temperature=0`, `seed=42` | 77.78% | 0.648 | 44.44% | 0.389 | **66.67% (deterministic)** |
| 2 | 2026-11-25 | `865bb38` + uncommitted | Embeddings → `bge-small-en-v1.5` | **77.78%** | **0.648** | 44.44% | **0.389** | 55.56% / 66.67% (2 runs) |
| 1 | 2026-11-25 | `865bb38` | Baseline | 55.56% | 0.472 | 44.44% | 0.306 | 77.78% (1 run) |

HR = Hit Rate@4. Answer acc. = share of answers containing every expected keyword.
Retrieval scores are deterministic. From Entry 3 on, answer accuracy is too
(temperature 0 + fixed seed). Entries 1–2 were sampled randomly and could vary
by 1–2 questions between runs.

⚠️ **Entry 5 changed the golden set and the scoring rules.** Compare scores from
Entry 5 onward with each other. Entries 1–4 were measured with the old golden set.

---

## Entry 8: Sentence chunking (2026-11-27)

### What changed

Only [src/chunker.py](../src/chunker.py) (`CHUNK_STRATEGY="sentence"`, now the
default). Same cleaned pages, size and overlap as Entry 7.

- Whole sentences are packed into chunks of up to 800 characters; a chunk never
  starts or ends mid-sentence.
- Overlap is the last whole sentence(s) of the previous chunk, up to 150 characters.
- Each page is split into roughly equal chunks, and a short final sentence (<200
  chars) joins the previous chunk instead of standing alone (max chunk 969 chars).
- Chunks are cut from the original text, so line breaks and code are kept.
- Chunks still stay within one page.

| | Entry 7 (fixed) | Entry 8 (sentence) |
|---|---|---|
| Chunks | 1,710 | 1,740 |
| Median length | 799 | 641 |
| Chunks under 200 chars | 55 | 5 (all whole short pages) |
| Chunks starting mid-sentence | 1,096 | 164 (pages that continue the previous page's sentence) |
| Chunks ending mid-sentence | 1,160 | 142 |

### Config snapshot

| Setting | Value |
|---|---|
| PDF extraction | `pypdfium2` + page cleanup |
| Chunking | **sentence packing**, `CHUNK_SIZE=800`, `CHUNK_OVERLAP=150`, per page |
| Chunks indexed | 1,740 |
| Embeddings | `BAAI/bge-small-en-v1.5`, query instruction prefix, normalized |
| Vector store | Chroma, cosine, `TOP_K=4` |
| Generation | Ollama `qwen2.5:1.5b`, `temperature=0`, `seed=42`, Entry 6 prompt |

### Results

```
Retrieval — by page:    Hit Rate: 88.89%   MRR: 0.639
           by content: Hit Rate: 88.89%   MRR: 0.694
Generation — Answer accuracy: 88.89%
```

| Question | Expected p. | Retrieved pages | Page | Content | Answer | Matched | vs Entry 7 (content) |
|---|---|---|---|---|---|---|---|
| variable | 31 | 36, 31, 29, 101 | HIT @2 | HIT @2 | PASS | name, value | ↑ 3 → 2 |
| function | 39 | 47, 39, 49, 40 | HIT @2 | HIT @1 | PASS | sequence, statements | = |
| recursion | 65 | 77, 66, 85, 79 | **MISS** | **MISS** | **FAIL** | — | ↓ 1 → miss |
| for loop | 53 | 206, 207, 113, 53 | **HIT @4** | **HIT @4** | PASS | repeat | ↑ miss → 4 (**first hit ever**) |
| while loop | 87 | 88, 87, 86, 87 | HIT @2 | HIT @2 | PASS | condition, repeat | = |
| string | 93 | 93, 111, 167, 26 | HIT @1 | HIT @1 | PASS | sequence, characters | = |
| list | 111 | 111, 122, 125, 111 | HIT @1 | HIT @1 | PASS | sequence, values | = |
| tuple | 137 | 137, 137, 144, 138 | HIT @1 | HIT @1 | PASS | sequence, values, immutable | = |
| dictionary | 125 | 125, 125, 142, 126 | HIT @1 | HIT @1 | PASS | key, value | = |

### Is it better than Entry 7?

**Scores: no.** Content MRR 0.759 → 0.694, page MRR 0.759 → 0.639, answers
100% → 88.89%. Hit rate is unchanged: one question gained (for loop), one lost
(recursion).

**Why recursion was lost.** The definition is still indexed, but its chunk ranks
**17th** (68.9%, was 1st at 76.8%). In Entry 7, the fixed window happened to cut
p.65 so that the definition sat in a short 327-character chunk. Now it sits
at the end of a 553-character chunk that is mostly the countdown walkthrough
("The countdown that got n=1 returns…"), and that text dominates the chunk's
single embedding. With no definition among its excerpts, the model answered
from general knowledge ("smaller instances… subproblems"), despite rule 4.

**What got better:** chunks are clean and whole. Glossary entries now come in
one piece; for tuple, chunk 3 is now the glossary entry "tuple: An immutable
sequence of elements." (In Entry 7 it was the end of another glossary and the
exercises.) The for-loop question hits for the first time.

**The real lesson: 9 questions are too few to rank chunking strategies.**
Every chunking change moves *which* sentences share an embedding, so a definition
can win or lose by luck of grouping. One question moving is ±11% hit rate and
up to ±0.11 MRR. Entry 7's recursion hit was partly lucky; Entry 8's miss is
partly unlucky.

### Experiment: chunk size and section-heading prefix (retrieval only, not indexed)

To see if this is noise or a trend, all chunkings were embedded in memory and
scored with exact search. The section-heading variant puts the latest
numbered heading (e.g. "5.8 Recursion") in front of each chunk's text before
embedding, carried across pages; the stored text is unchanged.

| Chunking | Chunks | Page HR / MRR | Content HR / MRR | Content rank per question (var, func, rec, for, while, str, list, tuple, dict) |
|---|---|---|---|---|
| fixed 800/150 (Entry 7) | 1,710 | 89% / 0.759 | 89% / 0.759 | 3, 1, 1, –, 2, 1, 1, 1, 1 |
| sentence 800/150 (Entry 8) | 1,740 | 78% / 0.611 | 78% / 0.667 | 2, 1, –, –, 2, 1, 1, 1, 1 |
| sentence 800/150 + heading | 1,740 | **100%** / 0.648 | **100%** / 0.704 | 2, 1, 2, 3, 2, 1, 1, 1, 2 |
| **sentence 600/120** | 2,251 | **100% / 0.722** | **100% / 0.722** | 2, 2, 2, 2, 2, 1, 1, 1, 1 |
| sentence 600/120 + heading | 2,251 | 100% / 0.759 | 100% / 0.676 | 3, 2, 2, 1, 4, 1, 1, 1, 2 |
| sentence 400/100 | 3,314 | 89% / 0.731 | 78% / 0.648 | 1, 3, –, 1, –, 1, 1, 2, 1 |
| sentence 400/100 + heading | 3,314 | 100% / 0.704 | 89% / 0.565 | 1, 2, 3, 2, –, 1, 1, 2, 4 |

Exact search differs slightly from Chroma's approximate (HNSW) index: here
sentence 800 misses the for loop, while the real index found it at rank 4.

- **Sentence 600/120 is the only setup that finds all 9 definitions** with every
  one at rank 1–2. Smaller chunks dilute a definition less.
- 400 is too small: definitions lose the context that makes them match.
- The heading prefix rescues recursion and for loop at 800, but its effect at
  600 is mixed. With 9 questions it can't be judged yet.

**Verdict:** keep sentence chunking (cleaner chunks, and it makes smaller sizes
safe). Next: try `CHUNK_SIZE=600`, `CHUNK_OVERLAP=120` as Entry 9, and grow the
golden set (including Think Stats / Think Bayes questions) before judging
section headings.

### Reference questions

Captured with `ask()` right after the evaluation (same index).

#### Q1. "What is a tuple in Python?"

**Answer**

> A tuple in Python is an immutable sequence of elements, which can be of any
> type. It is represented as a comma-separated list of values enclosed in
> parentheses. Tuples are immutable, meaning their elements cannot be changed
> after they are created. They can be created with no argument using the
> built-in function `tuple`, and single elements can be created by including a
> final comma. Tuple assignment allows swapping the values of two variables by
> creating a new tuple with the elements of the right side and assigning it to
> the left side variables.

| Rank | Source | Page | Similarity | Distance | Chunk length |
|---|---|---|---|---|---|
| 1 | thinkpython2.pdf | 137 | 82.8% | 0.172 | 619 chars |
| 2 | thinkpython2.pdf | 137 | 80.6% | 0.194 | 699 chars |
| 3 | thinkpython2.pdf | 144 | 78.5% | 0.215 | 396 chars |
| 4 | thinkpython2.pdf | 138 | 77.7% | 0.223 | 605 chars |

**vs Entry 7:** every chunk now starts and ends on a sentence. Chunk 3 is now
the glossary entry, and the answer opens with its exact wording ("An immutable
sequence of elements"). Entry 7's misstatement about replacing elements is gone
("their elements cannot be changed"). "Enclosed in parentheses" is presented as
required, though the book says it's optional. No `[n]` citations.

**Chunk 1: thinkpython2.pdf p.137 (82.8%)** (Chapter 12 opening, ends on the definition's first sentence)

```text
Chapter 12
Tuples
This chapter presents one more built-in type, the tuple, and then shows how lists, dictionaries, and tuples work together. I also present a useful feature for variable-length argument
lists, the gather and scatter operators.
One note: there is no consensus on how to pronounce “tuple”. Some people say “tuhple”, which rhymes with “supple”. But in the context of programming, most people say
“too-ple”, which rhymes with “quadruple”.
12.1 Tuples are immutable
A tuple is a sequence of values. The values can be any type, and they are indexed by
integers, so in that respect tuples are a lot like lists.
```

**Chunk 2: thinkpython2.pdf p.137 (80.6%)** (overlap sentence, then immutability and creation)

```text
The values can be any type, and they are indexed by
integers, so in that respect tuples are a lot like lists. The important difference is that tuples
are immutable.
Syntactically, a tuple is a comma-separated list of values:
>>> t = 'a', 'b', 'c', 'd', 'e'
Although it is not necessary, it is common to enclose tuples in parentheses:
>>> t = ('a', 'b', 'c', 'd', 'e')
To create a tuple with a single element, you have to include a final comma:
>>> t1 = 'a',
>>> type(t1)
<class 'tuple'>
A value in parentheses is not a tuple:
>>> t2 = ('a')
>>> type(t2)
<class 'str'>
Another way to create a tuple is the built-in function tuple. With no argument, it creates
an empty tuple:
>>> t = tuple()
>>> t
()
```

**Chunk 3: thinkpython2.pdf p.144 (78.5%)** (Chapter 12 glossary: tuple definitions)

```text
>>> d = dict(lt)
>>> structshape(d)
'dict of 3 int->str'
If you are having trouble keeping track of your data structures, structshape can help.
12.9 Glossary
tuple: An immutable sequence of elements.
tuple assignment: An assignment with a sequence on the right side and a tuple of variables on the left. The right side is evaluated and then its elements are assigned to the
variables on the left.
```

**Chunk 4: thinkpython2.pdf p.138 (77.7%)** (replacing a tuple, comparison, start of tuple assignment)

```text
But you can replace one
tuple with another:
>>> t = ('A',) + t[1:]
>>> t
('A', 'b', 'c', 'd', 'e')
This statement makes a new tuple and then makes t refer to it.
The relational operators work with tuples and other sequences; Python starts by comparing
the first element from each sequence. If they are equal, it goes on to the next elements, and
so on, until it finds elements that differ. Subsequent elements are not considered (even if
they are really big).
>>> (0, 1, 2) < (0, 3, 4)
True
>>> (0, 1, 2000000) < (0, 3, 4)
True
12.2 Tuple assignment
It is often useful to swap the values of two variables.
```

#### Q2. "What is recursion?"

**Answer**

> Recursion is a method of solving problems where the solution to a problem
> depends on solutions to smaller instances of the same problem. It involves
> breaking down a problem into smaller subproblems until the subproblems are
> simple enough to be solved directly. The solution to the original problem is
> then constructed from the solutions to the subproblems. This process is often
> accompanied by a base case, which is a condition that stops the recursion.

| Rank | Source | Page | Similarity | Distance | Chunk length |
|---|---|---|---|---|---|
| 1 | thinkpython2.pdf | 77 | 74.5% | 0.255 | 589 chars |
| 2 | thinkpython2.pdf | 66 | 74.3% | 0.257 | 614 chars |
| 3 | thinkpython2.pdf | 85 | 73.7% | 0.263 | 580 chars |
| 4 | thinkpython2.pdf | 79 | 72.9% | 0.271 | 351 chars |

**vs Entry 7:** the definition chunk (p.65) dropped out of the top 4; it ranks
17th. Its text is shown below for reference. The answer is back to a generic
CS definition, the same failure as Entries 1–4. Only "base case" (chunk 2)
comes from the book.

**Chunk 1: thinkpython2.pdf p.77 (74.5%)** (recursive definitions)

```text
Accordingly, it is known as the Turing
Thesis. For a more complete (and accurate) discussion of the Turing Thesis, I recommend
Michael Sipser’s book Introduction to the Theory of Computation.
To give you an idea of what you can do with the tools you have learned so far, we’ll evaluate a few recursively defined mathematical functions. A recursive definition is similar to
a circular definition, in the sense that the definition contains a reference to the thing being
defined. A truly circular definition is not very useful:
vorpal: An adjective used to describe something that is vorpal.
```

**Chunk 2: thinkpython2.pdf p.66 (74.3%)** (base case, start of infinite recursion)

```text
The bottom of the
stack, where n=0, is called the base case. It does not make a recursive call, so there are no
more frames.
As an exercise, draw a stack diagram for print_n called with s = 'Hello' and n=2. Then
write a function called do_n that takes a function object and a number, n, as arguments, and
that calls the given function n times.
5.10 Infinite recursion
If a recursion never reaches a base case, it goes on making recursive calls forever, and the
program never terminates. This is known as infinite recursion, and it is generally not a
good idea. Here is a minimal program with an infinite recursion:
```

**Chunk 3: thinkpython2.pdf p.85 (73.7%)** (Chapter 7 opening, mentions recursion in passing)

```text
Chapter 7
Iteration
This chapter is about iteration, which is the ability to run a block of statements repeatedly.
We saw a kind of iteration, using recursion, in Section 5.8. We saw another kind, using a
for loop, in Section 4.2. In this chapter we’ll see yet another kind, using a while statement.
But first I want to say a little more about variable assignment.
7.1 Reassignment
As you may have discovered, it is legal to make more than one assignment to the same
variable. A new assignment makes an existing variable refer to a new value (and stop
referring to the old value).
```

**Chunk 4: thinkpython2.pdf p.79 (72.9%)** (factorial, recursive leap of faith)

```text
The same is true of recursive programs. When you get to the recursive call, instead of
following the flow of execution, you should assume that the recursive call works (returns
the correct result) and then ask yourself, “Assuming that I can find the factorial of n − 1,
can I compute the factorial of n?” It is clear that you can, by multiplying by n.
```

**Not retrieved: the definition chunk, p.65, rank 17 (68.9%, 553 chars)**

```text
The execution of countdown begins with n=0, and since n is
not greater than 0, it outputs the word, “Blastoff!” and then
returns.
The countdown that got n=1 returns.
The countdown that got n=2 returns.
The countdown that got n=3 returns.
And then you’re back in __main__. So, the total output looks like this:
3
2
1
Blastoff!
A function that calls itself is recursive; the process of executing it is called recursion.
As another example, we can write a function that prints a string n times.
def print_n(s, n):
if n <= 0:
return
print(s)
print_n(s, n-1)
```

---

## Entry 7: Page cleanup at ingestion (2026-11-27)

### What changed

Only [src/ingest.py](../src/ingest.py). Chunking is still the fixed 800-character
window (run with `CHUNK_STRATEGY=fixed`), so this entry measures cleanup alone.

| Rule | Think Python | Think Stats | Think Bayes |
|---|---|---|---|
| Title and copyright pages (before the PDF's first bookmark) | 4 pages | 4 | 4 |
| Table of contents and index pages | 22 | 18 | 12 |
| Blank or header-only pages | 6 | 7 | 7 |
| Running header stripped from first line ("116 Chapter 12. Tuples") | 190 pages | 219 | 171 |
| **Pages kept** | 212 of 244 | 235 of 264 | 187 of 210 |

- Page numbers are unchanged (they are the PDF's own), so citations and the
  golden set stay valid. All 9 golden phrases are still on their expected pages.
- The Preface is kept; only pages before it are dropped.
- Known gap: one Think Stats page (p.245) keeps its header, because PDFium merged
  it into the first text line.

### Config snapshot

| Setting | Value |
|---|---|
| PDF extraction | `pypdfium2` + **page cleanup** |
| Chunking | fixed window, `CHUNK_SIZE=800`, `CHUNK_OVERLAP=150`, per page |
| Chunks indexed | **1,710** (was 1,912); 0 table-of-contents chunks (was 72) |
| Embeddings | `BAAI/bge-small-en-v1.5`, query instruction prefix, normalized |
| Vector store | Chroma, cosine, `TOP_K=4` |
| Generation | Ollama `qwen2.5:1.5b`, `temperature=0`, `seed=42`, Entry 6 prompt |

### Results

```
Retrieval — by page:    Hit Rate: 88.89%   MRR: 0.759
           by content: Hit Rate: 88.89%   MRR: 0.759
Generation — Answer accuracy: 100.00%
```

| Question | Expected p. | Retrieved pages | Page | Content | Answer | Matched |
|---|---|---|---|---|---|---|
| variable | 31 | 36, 101, 31, 29 | HIT @3 (was @2) | HIT @3 (was @2) | PASS | name, value |
| function | 39 | 39, 47, 41, 40 | HIT @1 | HIT @1 | PASS | sequence, statements |
| recursion | 65 | 65, 66, 86, 77 | HIT @1 | HIT @1 | PASS | calls itself |
| for loop | 53 | 86, 206, 113, 207 | MISS | MISS | PASS | each |
| while loop | 87 | 86, 87, 86, 88 | HIT @2 (was @1) | HIT @2 (was @1) | PASS | condition, repeat |
| string | 93 | 93, 29, 167, 26 | HIT @1 | HIT @1 | PASS | sequence, characters |
| list | 111 | 111, 122, 125, 111 | HIT @1 | HIT @1 | PASS | sequence, values |
| tuple | 137 | 137, 137, 145, 138 | HIT @1 | HIT @1 | PASS | sequence, values, immutable |
| dictionary | 125 | 125, 142, 134, 126 | HIT @1 | HIT @1 | PASS | key, value |

### Is it better than Entry 6?

**What it was for: yes.** The table of contents is gone from results. Recursion
had the TOC page (p.15) at rank 3; that slot now holds real content (p.77,
recursive definitions). The index is 11% smaller, and no chunk starts with a
running header any more.

**MRR: slightly down (0.833 → 0.759), but not because of lost content.** Hit rate
is unchanged and the same 8 questions hit. Two questions moved down one rank:

- **while loop (1 → 2):** removing the header shifted where the fixed windows cut
  p.86. Its last 326 characters ("…Another is the while statement. Here is a
  version of countdown that uses a while statement:") became a short, focused
  chunk that now ranks first (81.4%). It is about `while` but isn't the
  definition, which is on p.87 (80.7%).
- **variable (2 → 3):** the p.101 glossary chunk moved up after its window
  shifted. Rank 1 is still the p.36 glossary chunk, whose first line is
  "variable: A name that refers to a value", which is a correct answer, but the
  golden phrase is on p.31.

Both are artifacts of **where the fixed window happens to cut**, not of what
cleanup removed. The traces below show the problem: chunks start mid-word
("=3 returns.", "n frames have…", "een two functions…", "mputer scientists…").
This is what sentence chunking (Entry 8) addresses.

**Generation: unchanged at 100%.** Answers still rarely include `[n]` citations
(0/2 reference answers).

**Verdict:** keep cleanup. It removes noise the pipeline should never index.
The MRR drop comes from chunk-boundary noise, so measure Entry 8 before tuning
anything else.

### Reference questions

Captured with `ask()` right after the evaluation (same index). Ollama's prompt
cache means wording can differ slightly from the evaluation run; pass/fail does not.

#### Q1. "What is a tuple in Python?"

**Answer**

> A tuple in Python is a sequence of values, which can be of any type. It is
> syntactically a comma-separated list of values, and it is immutable. Tuples are
> created using parentheses, and a single element is created by including a final
> comma. Tuple elements can be replaced with another tuple, and the relational
> operators work with tuples and other sequences. Tuple assignment allows swapping
> the values of two variables by using tuple unpacking.

| Rank | Source | Page | Similarity | Distance | Chunk length |
|---|---|---|---|---|---|
| 1 | thinkpython2.pdf | 137 | 83.9% | 0.161 | 799 chars |
| 2 | thinkpython2.pdf | 137 | 82.1% | 0.179 | 559 chars |
| 3 | thinkpython2.pdf | 145 | 75.9% | 0.241 | 800 chars |
| 4 | thinkpython2.pdf | 138 | 75.4% | 0.246 | 800 chars |

**vs Entry 6:** same top 2 chunks (p.137 had no running header, it's a chapter
opening). Ranks 3 and 4 swapped. The answer is 5 sentences (was 10), all from
the excerpts, but "Tuple elements can be replaced with another tuple" slightly
misstates chunk 4 (you can't modify elements; you can replace the whole tuple).
No `[n]` citations.

**Chunk 1: thinkpython2.pdf p.137 (83.9%)** (Chapter 12 opening, contains the definition)

```text
Chapter 12
Tuples
This chapter presents one more built-in type, the tuple, and then shows how lists, dictionaries, and tuples work together. I also present a useful feature for variable-length argument
lists, the gather and scatter operators.
One note: there is no consensus on how to pronounce “tuple”. Some people say “tuhple”, which rhymes with “supple”. But in the context of programming, most people say
“too-ple”, which rhymes with “quadruple”.
12.1 Tuples are immutable
A tuple is a sequence of values. The values can be any type, and they are indexed by
integers, so in that respect tuples are a lot like lists. The important difference is that tuples
are immutable.
Syntactically, a tuple is a comma-separated list of values:
>>> t = 'a', 'b', 'c', 'd', 'e'
Although it is not necessary, it
```

**Chunk 2: thinkpython2.pdf p.137 (82.1%)** (rest of the same page, overlaps chunk 1)

```text
at tuples
are immutable.
Syntactically, a tuple is a comma-separated list of values:
>>> t = 'a', 'b', 'c', 'd', 'e'
Although it is not necessary, it is common to enclose tuples in parentheses:
>>> t = ('a', 'b', 'c', 'd', 'e')
To create a tuple with a single element, you have to include a final comma:
>>> t1 = 'a',
>>> type(t1)
<class 'tuple'>
A value in parentheses is not a tuple:
>>> t2 = ('a')
>>> type(t2)
<class 'str'>
Another way to create a tuple is the built-in function tuple. With no argument, it creates
an empty tuple:
>>> t = tuple()
>>> t
()
```

**Chunk 3: thinkpython2.pdf p.145 (75.9%)** (Chapter 12 glossary and exercises, header now stripped)

```text
gather: An operation that collects multiple arguments into a tuple.
scatter: An operation that makes a sequence behave like multiple arguments.
zip object: The result of calling a built-in function zip; an object that iterates through a
sequence of tuples.
iterator: An object that can iterate through a sequence, but which does not provide list
operators and methods.
data structure: A collection of related values, often organized in lists, dictionaries, tuples,
etc.
shape error: An error caused because a value has the wrong shape; that is, the wrong type
or size.
12.10 Exercises
Exercise 12.1. Write a function called most_frequent that takes a string and prints the letters in decreasing order of frequency. Find text samples from several different languages and see
how letter frequency varie
```

**Chunk 4: thinkpython2.pdf p.138 (75.4%)** (replacing a tuple, comparison, start of tuple assignment)

```text
n’t modify the elements. But you can replace one
tuple with another:
>>> t = ('A',) + t[1:]
>>> t
('A', 'b', 'c', 'd', 'e')
This statement makes a new tuple and then makes t refer to it.
The relational operators work with tuples and other sequences; Python starts by comparing
the first element from each sequence. If they are equal, it goes on to the next elements, and
so on, until it finds elements that differ. Subsequent elements are not considered (even if
they are really big).
>>> (0, 1, 2) < (0, 3, 4)
True
>>> (0, 1, 2000000) < (0, 3, 4)
True
12.2 Tuple assignment
It is often useful to swap the values of two variables. With conventional assignments, you
have to use a temporary variable. For example, to swap a and b:
>>> temp = a
>>> a = b
>>> b = temp
This solution is cumbersome; tuple
```

#### Q2. "What is recursion?"

**Answer**

> Recursion is a process where a function calls itself repeatedly until a base
> case is reached. The base case is the simplest instance of the problem that
> does not require further recursion. The process of executing a recursive
> function is called recursion.

| Rank | Source | Page | Similarity | Distance | Chunk length |
|---|---|---|---|---|---|
| 1 | thinkpython2.pdf | 65 | 76.8% | 0.232 | 327 chars |
| 2 | thinkpython2.pdf | 66 | 75.0% | 0.250 | 666 chars |
| 3 | thinkpython2.pdf | 86 | 72.8% | 0.272 | 326 chars |
| 4 | thinkpython2.pdf | 77 | 72.4% | 0.276 | 800 chars |

**vs Entry 6:** the table of contents (p.15, rank 3) is gone, replaced by p.77
on recursive definitions. The book's definition is now in a short, focused
chunk 1 (327 chars), and its similarity rose from 75.6% to 76.8%. The answer's
last sentence now echoes the book ("the process of executing … is called
recursion"), but it still doesn't quote "A function that calls itself is
recursive", and "simplest instance of the problem" is still the model's own.
No citations.

**Chunk 1: thinkpython2.pdf p.65 (76.8%)** (end of p.65, contains the book's definition)

```text
=3 returns.
And then you’re back in __main__. So, the total output looks like this:
3
2
1
Blastoff!
A function that calls itself is recursive; the process of executing it is called recursion.
As another example, we can write a function that prints a string n times.
def print_n(s, n):
if n <= 0:
return
print(s)
print_n(s, n-1)
```

**Chunk 2: thinkpython2.pdf p.66 (75.0%)** (base case, start of infinite recursion)

```text
n frames have different values for the parameter n. The bottom of the
stack, where n=0, is called the base case. It does not make a recursive call, so there are no
more frames.
As an exercise, draw a stack diagram for print_n called with s = 'Hello' and n=2. Then
write a function called do_n that takes a function object and a number, n, as arguments, and
that calls the given function n times.
5.10 Infinite recursion
If a recursion never reaches a base case, it goes on making recursive calls forever, and the
program never terminates. This is known as infinite recursion, and it is generally not a
good idea. Here is a minimal program with an infinite recursion:
```

**Chunk 3: thinkpython2.pdf p.86 (72.8%)** (end of p.86, mentions recursion in passing)

```text
een two functions, countdown and print_n, that iterate using recursion.
Because iteration is so common, Python provides language features to make it easier. One
is the for statement we saw in Section 4.2. We’ll get back to that later.
Another is the while statement. Here is a version of countdown that uses a while statement:
```

**Chunk 4: thinkpython2.pdf p.77 (72.4%)** (recursive definitions, replaces the TOC chunk)

```text
mputer scientists (some would argue that he was a mathematician, but a lot of early
computer scientists started as mathematicians). Accordingly, it is known as the Turing
Thesis. For a more complete (and accurate) discussion of the Turing Thesis, I recommend
Michael Sipser’s book Introduction to the Theory of Computation.
To give you an idea of what you can do with the tools you have learned so far, we’ll evaluate a few recursively defined mathematical functions. A recursive definition is similar to
a circular definition, in the sense that the definition contains a reference to the thing being
defined. A truly circular definition is not very useful:
vorpal: An adjective used to describe something that is vorpal.
If you saw that definition in the dictionary, you might be annoyed. On the oth
```

---

## Entry 6: Prompt with numbered excerpts, citations and book wording (2026-11-26)

### What changed

Only [src/generator.py](../src/generator.py). Retrieval, chunks and golden set are
the same as Entry 5.

- Excerpts are numbered `[1]`–`[4]` with source and page. `[n]` = `sources[n-1]`
  in the API response.
- New system prompt with 5 rules: only facts from the excerpts, the book's own
  wording for definitions, cite `[n]` after each sentence, a fixed reply
  ("I couldn't find this in the books.") when the answer isn't there, and 2–5
  sentences.
- The key rules are repeated after the question, because small models follow the
  last instruction best.
- The API response shape is unchanged.

### Results

```
Retrieval — unchanged from Entry 5 (page 88.89% / 0.833, content 88.89% / 0.833)
Generation — Answer accuracy: 100.00%
Citations — answers containing at least one [n]: 1/9
```

| Question | Answer | Matched | Cites | Grounded in the book's wording? |
|---|---|---|---|---|
| variable | "A variable in Python is a name that refers to a value." | name, value | — | **Verbatim** book definition |
| function | "…a named sequence of statements that performs some useful operation…" | sequence, statements | — | Close to verbatim |
| recursion | "…a process where a function calls itself repeatedly until a base case is reached…" | calls itself | — | Partly. "Calls itself" and "base case" come from excerpts [1]/[4]; "simplest instance of the problem" doesn't |
| for loop | "…iterates over a sequence … executes the loop body for each element…" | each | — | General knowledge. Retrieval still misses p.53 |
| while loop | "…repeatedly execute a block of code as long as a specified condition is true… The body of the loop should change the value of one or more variables…" | condition, repeat | — | Mostly. The last sentence is verbatim from p.87 |
| string | "…an ordered collection of characters…" | sequence, characters | **[1]** | Partly. Paraphrases "sequence"; the example is from the book |
| list | "A list in Python is a sequence of values… [10, 20, 30, 40]… 'crunchy frog'…" | sequence, values | — | **Verbatim** definition and examples |
| tuple | "A tuple in Python is a sequence of values. The values can be any type… The important difference is that tuples are immutable…" | sequence, values, immutable | — | **Verbatim**. Too long (10 sentences, limit was 5) |
| dictionary | "…a mapping where each key is associated with a single value… a collection of indices (keys) and values…" | key, value | — | Mostly. Adds a hashtable fact from another excerpt |

### Is it better than the old prompt?

**Grounding: yes, clearly.** Under Entry 5's scoring the old prompt passed 8/9;
the new one passes 9/9. More important than the score, answers now **reuse the
book's sentences**. Variable, list and tuple are almost word for word, and
recursion is no longer a generic CS definition: it uses the book's "calls
itself" and "base case".

**Citations: mostly not.** Only the string answer contains `[1]`. The 1.5B model
follows "use the book's wording" but ignores "cite after each sentence" and
"2–5 sentences" (tuple ran to 10). The prompt's citation rules are correct but
beyond what `qwen2.5:1.5b` reliably follows. The app can't link claims to
sources yet.

**Note:** the 100% is keyword-based. It shows each answer contains the key
concepts; it doesn't check grounding or citations. That's why the citation rate
is logged separately from now on.

**Verdict:** keep the new prompt. Next: measure citations properly and make them
reliable, by trying a larger model (`qwen2.5:3b`/`7b`, or Claude) and/or
structured output that forces a citation list.

### Reference questions

The chunks are **identical to Entry 4** (same index, same retrieval), so see
Entry 4 for their full text. Answers come from the evaluation run.

#### Q1. "What is a tuple in Python?"

> A tuple in Python is a sequence of values. The values can be any type, and they
> are indexed by integers, so in that respect tuples are a lot like lists. The
> important difference is that tuples are immutable. Syntactically, a tuple is a
> comma-separated list of values. Although it is not necessary, it is common to
> enclose tuples in parentheses. To create a tuple with a single element, you have
> to include a final comma. A value in parentheses is not a tuple. The built-in
> function tuple creates an empty tuple with no argument. Tuples are immutable,
> meaning they cannot be modified once created.

| Rank | Source | Page | Similarity |
|---|---|---|---|
| 1 | thinkpython2.pdf | 137 | 83.9% |
| 2 | thinkpython2.pdf | 137 | 82.1% |
| 3 | thinkpython2.pdf | 138 | 78.1% |
| 4 | thinkpython2.pdf | 145 | 76.8% |

**vs Entry 4:** "ordered collection of values" (paraphrase) became the book's
exact "A tuple is a sequence of values… The important difference is that tuples
are immutable". Every sentence traces to chunks 1–2. There are no `[n]`
citations, and it's twice the requested length.

#### Q2. "What is recursion?"

> Recursion is a process where a function calls itself repeatedly until a base
> case is reached. The base case is the simplest instance of the problem that
> does not require further recursion. The process of repeatedly calling the
> function until the base case is reached is called recursion.

| Rank | Source | Page | Similarity |
|---|---|---|---|
| 1 | thinkpython2.pdf | 65 | 75.6% |
| 2 | thinkpython2.pdf | 86 | 74.5% |
| 3 | thinkpython2.pdf | 15 | 72.8% |
| 4 | thinkpython2.pdf | 66 | 72.3% |

**vs Entry 4:** the answer moved from a fully generic definition ("smaller
instances… subproblems… solved directly") to one built from the excerpts:
"calls itself" (chunk 1) and "base case" (chunk 4). It still doesn't quote the
book's sentence "A function that calls itself is recursive", and "simplest
instance of the problem" is the model's own addition. There are no citations.

---

## Entry 5: Golden set fixes + keyword synonym groups (2026-11-26)

### What changed

This entry changes **only the measurement**. Pipeline, index and prompt are the
same as Entry 4.

**Golden set** ([src/eval_data.py](../src/eval_data.py)). Every phrase was
verified as the book's exact wording on its page, in the pypdfium2 text:

| Question | Before | After | Why |
|---|---|---|---|
| recursion | phrase `calls itself` | `a function that calls itself is recursive` | The old phrase also matched the countdown walkthrough (pp.65–66, 162); the new one is the definition |
| for loop | p.52, `for i in range` | **p.53**, `a for statement is also called a loop` | The old phrase was code found in 28 chunks across 3 books; the definition is on p.53 |
| while loop | p.86, `while n > 0` | **p.87**, `flow of execution for a while statement` | The old phrase was on p.87 while the page said 86 |

**Keyword groups:** each keyword is now a group of accepted alternatives, all
taken from the book's own wording. The answer must match every group.

| Question | Before | After |
|---|---|---|
| variable | `name`, `value` | [name] [value] |
| function | `sequence`, `statements` | [sequence / series] [statements] |
| recursion | `calls itself` | [calls itself / call itself / calling itself] |
| for loop | `repeat` | [repeat / loops back / each / every / again] |
| while loop | `repeat` | [condition] [repeat / as long as / until / go back / loops back] (**stricter**: must mention the condition) |
| string | `sequence`, `characters` | [sequence / ordered collection] [characters] |
| list | `sequence`, `values` | [sequence / ordered collection] [values / elements / items] |
| tuple | `sequence`, `values` | [sequence / ordered collection] [values / elements] [immutable] (**stricter**: the book's key difference from lists) |
| dictionary | `list` | [key] [value] (tests the actual definition, not "is like a list") |

**Scoring** ([src/evaluator.py](../src/evaluator.py)):
- The content check lowercases and collapses whitespace on both sides, so a
  phrase that wraps onto a new line in the PDF still matches. The wording must
  still be exact.
- Keywords match at a word start: `each` doesn't match "reach", but `repeat`
  matches "repeatedly".

### Results

```
Retrieval — by page:    Hit Rate: 88.89%   MRR: 0.833
           by content: Hit Rate: 88.89%   MRR: 0.833
Generation — Answer accuracy: 88.89%
```

| Question | Expected p. | Retrieved pages | Page | Content | Answer | Matched |
|---|---|---|---|---|---|---|
| variable | 31 | 36, 31, 101, 41 | HIT @2 | HIT @2 | PASS | name, value |
| function | 39 | 39, 47, 41, 40 | HIT @1 | HIT @1 | PASS | sequence, statements |
| recursion | 65 | 65, 86, 15, 66 | HIT @1 | HIT @1 | **FAIL** | — |
| for loop | **53** | 86, 113, 128, 97 | MISS | MISS | PASS | each |
| while loop | **87** | 87, 86, 86, 88 | HIT @1 | HIT @1 | PASS | condition, repeat |
| string | 93 | 93, 29, 99, 167 | HIT @1 | HIT @1 | PASS | sequence, characters |
| list | 111 | 111, 122, 126, 125 | HIT @1 | HIT @1 | PASS | sequence, values |
| tuple | 137 | 137, 137, 138, 145 | HIT @1 | HIT @1 | PASS | ordered collection, values, immutable |
| dictionary | 125 | 125, 126, 134, 142 | HIT @1 | HIT @1 | PASS | key, value |

### What the new scoring shows

- **Answers: 55.56% → 88.89% with identical answers.** Entry 4's tuple and
  dictionary failures were correct answers rejected by the old keywords. Now
  only **recursion** fails, and it is the real failure: the answer ignores the
  rank-1 definition (see Entry 4).
- **Retrieval:** page MRR rose from 0.778 to 0.833 because the while loop's page
  label is now correct (p.87 at rank 1). The recursion content hit survived the
  stricter phrase, so the definition sentence itself is at rank 1.
- **The for loop is still a real retrieval miss.** p.53 isn't in the top 4, yet
  the answer passes on `each`. This is a known limit of keyword scoring: a
  correct general-knowledge answer passes even when retrieval failed.

This is the baseline the prompt change (Entry 6) is measured against.

---

## Entry 4: PDF extraction → pypdfium2 (2026-11-26)

### What changed

- [src/ingest.py](../src/ingest.py): text extraction now uses **pypdfium2 5.15.2**
  (PDFium, Chrome's PDF engine) instead of **pypdf 5.6.0**. PDFium places word
  gaps from each character's actual position, so words printed in code font keep
  their spaces.
- New text cleanup at ingestion:
  - `\r\n` → `\n`
  - words hyphenated across a line are rejoined (PDFium's U+FFFE marker removed)
  - private-use glyph fragments removed
  - TeX T1 control codes translated: Think Bayes' ligatures (`\x1e` → "ffi",
    `\x1b` → "ff", `\x1c` → "fi", …), quotes, dashes and bullets. These were
    broken with pypdf too: 750 characters on 171 pages ("di\x1ecult" for "difficult").
- `requirements.txt`: `pypdf==5.6.0` → `pypdfium2==5.15.2`. Full re-index run.

### What the extraction change fixed, by example

| Book text | pypdf | pypdfium2 |
|---|---|---|
| p.111 "a list is a sequence of values" | `alistis a sequence of values` | `a list is a sequence of values` |
| p.125 "A dictionary is like a list" | `Adictionaryis like a list` | `A dictionary is like a list` |
| p.86 "7.3 The while statement" | `7.3 Thewhilestatement` | `7.3 The while statement` |
| p.65 "calls itself is recursive" | `calls itself isrecursive` | `calls itself is recursive` |
| Think Bayes "equally difficult" | `equally di\x1ecult` | `equally difficult` |

Golden phrases found in the text of their expected page: **6/9 → 8/9**. The
remaining one is a golden-set mismatch: the while-loop phrase `while n > 0` is
on p.87, not the expected p.86.

### Config snapshot

Same as Entry 3 except:

| Area | Setting |
|---|---|
| Ingestion | **pypdfium2 5.15.2** `get_text_range()`, one record per page (PDF index, 1-based), cleanup as above |
| Index contents | 1,912 chunks: thinkpython2.pdf 750 · thinkstats2.pdf 639 · thinkbayes.pdf 523 (single segment folder `55bc3e73-…`) |

### Results

```
Retrieval — by page:    Hit Rate: 88.89%   MRR: 0.778
           by content: Hit Rate: 88.89%   MRR: 0.833
Generation — Answer accuracy: 55.56%  (identical on 2 back-to-back runs, 9/9 same answer text)
```

| Question | Expected p. | Retrieved pages | Page | Content | Answer | vs Entry 3 (page / content / answer) |
|---|---|---|---|---|---|---|
| What is a variable in Python? | 31 | 36, 31, 101, 41 | HIT @2 | HIT @2 | PASS | same / same / same |
| What is a function in Python? | 39 | 39, 47, 41, 40 | HIT @1 | HIT @1 | PASS | **better** (@3 → @1) / same / same |
| What is recursion? | 65 | 65, 86, 15, 66 | HIT @1 | HIT @1 | FAIL | **fixed** / **fixed** / **worse** |
| What does a for loop do in Python? | 52 | 86, 113, 128, 97 | MISS | MISS | FAIL | same / same / same |
| What does a while loop do in Python? | 86 | 87, 86, 86, 88 | HIT @2 | HIT @1 | PASS | worse (@1 → @2) / **fixed** / **better** |
| What is a string in Python? | 93 | 93, 29, 99, 167 | HIT @1 | HIT @1 | PASS | same / same / same |
| What is a list in Python? | 111 | 111, 122, 126, 125 | HIT @1 | HIT @1 | PASS | same / **fixed** / same |
| What is a tuple in Python? | 137 | 137, 137, 138, 145 | HIT @1 | HIT @1 | FAIL | same / same / same |
| What is a dictionary in Python? | 125 | 125, 126, 134, 142 | HIT @1 | HIT @1 | FAIL | same / **fixed** / **worse** |

### Is it better than pypdf?

**Retrieval: yes, by a lot.** Content Hit Rate doubled (44.4% → 88.9%) and content
MRR more than doubled (0.389 → 0.833). It's partly a measurement fix and partly a
real improvement:

- **Measurement fix:** list and dictionary were impossible before, because their
  phrases didn't exist in any chunk ("alistis", "Adictionaryis"). They now hit at
  rank 1.
- **Real improvement:** recursion moved from MISS to **rank 1**. The chunk with the
  book's own definition ("A function that calls itself is recursive") is now
  retrieved first, because the embedding sees "is recursive" instead of
  "isrecursive". Function improved from rank 3 to rank 1.
- Only the for loop is still missed on both checks, and its expected phrase
  (`for i in range`) is weak (see Entry 3).

**Answer accuracy: down from 66.67% to 55.56%, but not because answers got
worse.** Generation is deterministic, so the changed context caused these
differences, not luck. Of the 4 failures:

| Question | Answer (abridged) | Verdict |
|---|---|---|
| recursion | "…a method of solving problems where the solution … depends on solutions to smaller instances of the same problem…" | **Real failure: ungrounded.** The book's definition is in chunk 1 at rank 1, and the model ignores it and answers from its own training |
| for loop | "…iterates over a sequence … perform an action on each element…" | Correct in general, but retrieval missed p.52 and the answer never says `repeat` |
| tuple | "…an **ordered collection** of values…" | Correct, but paraphrases the book's "sequence of values" |
| dictionary | "…a collection of key-value pairs … map keys to values…" | Correct. The keyword `list` (from "like a list") is a weak test for a dictionary definition |

So better retrieval made the generation score look worse. Two failures are correct
answers rejected by the keyword check, and the one real failure (recursion) is
the 1.5B model not following the "answer only from context" instruction, even
when the right sentence is ranked first.

**Verdict:** keep pypdfium2. With retrieval at 89%, **generation is now the
bottleneck**, both the model and how it's scored.

### Note on determinism

Two full `evaluate` runs gave identical answers (9/9). But asking the same
question in a *different order* of calls can change the wording slightly (seen on
the tuple question below), because Ollama reuses its prompt cache between
requests. Pass/fail was the same either way. For comparable scores, always use
the full `python main.py evaluate` run.

### Reference questions (with full chunks)

All answers and chunks below come from one `ask()` call per question.

#### Q1. "What is a tuple in Python?"

**Answer**

> A tuple in Python is an ordered collection of values, which can be of any type.
> It is created by enclosing the values in parentheses or by using the built-in
> function `tuple`. Tuples are immutable, meaning their elements cannot be
> changed after they are created. They can be created with a single element by
> adding a trailing comma. Tuples are often used to group related values together
> and can be used in place of lists for certain operations.

| Rank | Source | Page | Similarity | Distance | Chunk length |
|---|---|---|---|---|---|
| 1 | thinkpython2.pdf | 137 | 83.9% | 0.161 | 799 chars |
| 2 | thinkpython2.pdf | 137 | 82.1% | 0.179 | 559 chars |
| 3 | thinkpython2.pdf | 138 | 78.1% | 0.219 | 800 chars |
| 4 | thinkpython2.pdf | 145 | 76.8% | 0.232 | 800 chars |

**Chunk 1: thinkpython2.pdf p.137 (83.9%)** (Chapter 12 opening, contains the definition)

```text
Chapter 12
Tuples
This chapter presents one more built-in type, the tuple, and then shows how lists, dictionaries, and tuples work together. I also present a useful feature for variable-length argument
lists, the gather and scatter operators.
One note: there is no consensus on how to pronounce “tuple”. Some people say “tuhple”, which rhymes with “supple”. But in the context of programming, most people say
“too-ple”, which rhymes with “quadruple”.
12.1 Tuples are immutable
A tuple is a sequence of values. The values can be any type, and they are indexed by
integers, so in that respect tuples are a lot like lists. The important difference is that tuples
are immutable.
Syntactically, a tuple is a comma-separated list of values:
>>> t = 'a', 'b', 'c', 'd', 'e'
Although it is not necessary, it
```

**Chunk 2: thinkpython2.pdf p.137 (82.1%)** (rest of the same page, overlaps chunk 1)

```text
at tuples
are immutable.
Syntactically, a tuple is a comma-separated list of values:
>>> t = 'a', 'b', 'c', 'd', 'e'
Although it is not necessary, it is common to enclose tuples in parentheses:
>>> t = ('a', 'b', 'c', 'd', 'e')
To create a tuple with a single element, you have to include a final comma:
>>> t1 = 'a',
>>> type(t1)
<class 'tuple'>
A value in parentheses is not a tuple:
>>> t2 = ('a')
>>> type(t2)
<class 'str'>
Another way to create a tuple is the built-in function tuple. With no argument, it creates
an empty tuple:
>>> t = tuple()
>>> t
()
```

**Chunk 3: thinkpython2.pdf p.138 (78.1%)** (tuple() from a sequence, indexing, immutability)

```text
116 Chapter 12. Tuples
If the argument is a sequence (string, list or tuple), the result is a tuple with the elements of
the sequence:
>>> t = tuple('lupins')
>>> t
('l', 'u', 'p', 'i', 'n', 's')
Because tuple is the name of a built-in function, you should avoid using it as a variable
name.
Most list operators also work on tuples. The bracket operator indexes an element:
>>> t = ('a', 'b', 'c', 'd', 'e')
>>> t[0]
'a'
And the slice operator selects a range of elements.
>>> t[1:3]
('b', 'c')
But if you try to modify one of the elements of the tuple, you get an error:
>>> t[0] = 'A'
TypeError: object doesn't support item assignment
Because tuples are immutable, you can’t modify the elements. But you can replace one
tuple with another:
>>> t = ('A',) + t[1:]
>>> t
('A', 'b', 'c', 'd', 'e')
Thi
```

**Chunk 4: thinkpython2.pdf p.145 (76.8%)** (Chapter 12 glossary and exercises)

```text
12.10. Exercises 123
gather: An operation that collects multiple arguments into a tuple.
scatter: An operation that makes a sequence behave like multiple arguments.
zip object: The result of calling a built-in function zip; an object that iterates through a
sequence of tuples.
iterator: An object that can iterate through a sequence, but which does not provide list
operators and methods.
data structure: A collection of related values, often organized in lists, dictionaries, tuples,
etc.
shape error: An error caused because a value has the wrong shape; that is, the wrong type
or size.
12.10 Exercises
Exercise 12.1. Write a function called most_frequent that takes a string and prints the letters in decreasing order of frequency. Find text samples from several different languages and see
how l
```

**Q1 vs Entry 2:** the code is now readable (`t = 'a', 'b', 'c'` instead of
`t ='a','b','c'`, `<class 'tuple'>` instead of `<class'tuple'>`), and
"dictionar-ies" and "tuh-ple" are rejoined. Chunk 3 (p.138: indexing,
slicing, immutability error) replaced the debugging chunk from p.144, a more
useful context. The answer is now fuller and correct (single-element comma,
`tuple()`, immutability). Every fact in it is in the chunks except "ordered
collection", its paraphrase of "sequence".

#### Q2. "What is recursion?"

**Answer**

> Recursion is a method of solving problems where the solution to a problem
> depends on solutions to smaller instances of the same problem. It involves
> breaking down a problem into smaller subproblems until the subproblems are
> simple enough to be solved directly. The process of solving the subproblems is
> called recursion.

| Rank | Source | Page | Similarity | Distance | Chunk length |
|---|---|---|---|---|---|
| 1 | thinkpython2.pdf | 65 | 75.6% | 0.244 | 345 chars |
| 2 | thinkpython2.pdf | 86 | 74.5% | 0.255 | 350 chars |
| 3 | thinkpython2.pdf | 15 | 72.8% | 0.272 | 799 chars |
| 4 | thinkpython2.pdf | 66 | 72.3% | 0.277 | 707 chars |

**Chunk 1: thinkpython2.pdf p.65 (75.6%)** (the book's definition of recursion)

```text
untdown that got n=3 returns.
And then you’re back in __main__. So, the total output looks like this:
3
2
1
Blastoff!
A function that calls itself is recursive; the process of executing it is called recursion.
As another example, we can write a function that prints a string n times.
def print_n(s, n):
if n <= 0:
return
print(s)
print_n(s, n-1)
```

**Chunk 2: thinkpython2.pdf p.86 (74.5%)** (Chapter 7 intro, mentions recursion in passing)

```text
ation.
We have already seen two functions, countdown and print_n, that iterate using recursion.
Because iteration is so common, Python provides language features to make it easier. One
is the for statement we saw in Section 4.2. We’ll get back to that later.
Another is the while statement. Here is a version of countdown that uses a while statement:
```

**Chunk 3: thinkpython2.pdf p.15 (72.8%)** (table of contents)

```text
. . . . . . . . . . . 42
5.8 Recursion . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 43
5.9 Stack diagrams for recursive functions . . . . . . . . . . . . . . . . . . . . . 44
5.10 Infinite recursion . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 44
5.11 Keyboard input . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 45
5.12 Debugging . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 46
5.13 Glossary . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 47
5.14 Exercises . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 47
6 Fruitful functions 51
6.1 Return values . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 51
6.2 Incremental
```

**Chunk 4: thinkpython2.pdf p.66 (72.3%)** (base case, start of infinite recursion)

```text
ss any arguments to it.
The four countdown frames have different values for the parameter n. The bottom of the
stack, where n=0, is called the base case. It does not make a recursive call, so there are no
more frames.
As an exercise, draw a stack diagram for print_n called with s = 'Hello' and n=2. Then
write a function called do_n that takes a function object and a number, n, as arguments, and
that calls the given function n times.
5.10 Infinite recursion
If a recursion never reaches a base case, it goes on making recursive calls forever, and the
program never terminates. This is known as infinite recursion, and it is generally not a
good idea. Here is a minimal program with an infinite recursion:
```

**Q2 vs Entry 2:** retrieval is fixed. The defining sentence "A function that
calls itself is recursive; the process of executing it is called recursion" is
now **rank 1** (it wasn't in the top 4 before), and chunk 4 adds the base case.
**The answer is still ungrounded.** Every sentence of it is a general textbook
definition from the model's training: "smaller instances", "subproblems" and
"solved directly" appear in no chunk. The context now holds everything needed for
a correct, book-grounded answer, so this is purely a generation problem. The
table of contents (chunk 3) still takes a slot.

### Observations

- Retrieval went from the weakest stage to the strongest. Both hit rates are at
  89%, and the only miss (for loop) has a weak golden phrase.
- **Generation is now the bottleneck.** The keyword check rejects 2 correct
  answers (tuple, dictionary), and the model ignores a rank-1 definition
  (recursion).
- Next steps, in order:
  1. Fix the golden set: phrases for recursion, for loop and while (page/phrase
     mismatch), and accept synonyms for answer keywords (`sequence` OR `ordered
     collection`, `repeat` OR `as long as`).
  2. Tighten the prompt: number the chunks, require a citation per claim, and say
     to use the book's own wording for definitions.
  3. Try a larger local model (`qwen2.5:3b` / `7b`) or Claude, logging each as its
     own entry.
  4. Drop table-of-contents chunks and duplicate pages from the top 4.

---

## Entry 3: Deterministic generation (2026-11-25)

### What changed

- Ollama requests now send `options: {temperature: 0, seed: 42}`
  (`OLLAMA_TEMPERATURE` / `OLLAMA_SEED` in config). Retrieval is unchanged from Entry 2.

### Why this makes scores comparable

An LLM writes its answer one token at a time. At each step it computes a
probability for every possible next token, then **samples** one:

- **Temperature** controls how random that pick is. Above 0, a lower-probability
  token is sometimes chosen ("a sequence of *values*" one run, "*elements*" the
  next), and once one word differs, every later word can differ too. At **0** it
  always takes the most likely token (greedy decoding).
- **Seed** fixes the random number generator behind any sampling that's left, so
  even that is repeated exactly.

With both fixed, **the same prompt gives the same answer**. The prompt is the
question plus the retrieved chunks, so when the answer score changes between two
entries, the cause must be something you changed (chunks, prompt or model), not
luck. Before this, Entry 2 scored 55.56% and then 66.67% on an identical index,
which was larger than the effects we were trying to measure.

Limits: this is repeatable on **this machine with this Ollama version and model
digest**. Upgrading Ollama, changing hardware, or re-pulling the model can shift
answers, so log those as changes. Temperature 0 also doesn't make answers
*correct*, only consistent.

### Results

```
Retrieval — by page:    Hit Rate: 77.78%   MRR: 0.648
           by content: Hit Rate: 44.44%   MRR: 0.389
Generation — Answer accuracy: 66.67%  (identical on 2 back-to-back runs)
```

Verified: 2 full `evaluate` runs gave the same pass/fail per question
(P P P F F P P F P), and asking each of the 9 questions twice gave **9/9
identical answer texts**.

| Question | Answer | Why it fails |
|---|---|---|
| What does a for loop do in Python? | FAIL | Retrieval miss. The answer comes from the model's own knowledge (mentions `i`/`j`/`k` and `set`, and says `continue` "exits early", which is wrong) |
| What does a while loop do in Python? | FAIL | Correct ("continues to execute … as long as a condition is true") but doesn't use the word `repeat`: a keyword false negative |
| What is a tuple in Python? | FAIL | Says "sequence of elements" (from the book's glossary), not `values`: a keyword false negative |

**66.67% is the new baseline to beat.** Two of the three failures are the keyword
check being too strict, not wrong answers. The for-loop failure is a real one
caused by retrieval.

---

## Entry 2: Embedding model → BGE small (2026-11-25)

### What changed

- `EMBEDDING_MODEL`: `all-MiniLM-L6-v2` → `BAAI/bge-small-en-v1.5` (same 384 dims).
- Questions are embedded with BGE's query prefix (`QUERY_INSTRUCTION` =
  "Represent this sentence for searching relevant passages: "). Chunks are embedded
  without it.
- Embeddings use `normalize_embeddings=True`.
- `python main.py index` now deletes stale `storage/<uuid>/` folders. After the
  re-index, `storage/` holds one segment folder (`bbb3b4f8-…`) instead of 8.
  `chroma.sqlite3` grew from 41 MB to 55 MB, because SQLite doesn't reclaim
  deleted space.

### Config snapshot

Same as Entry 1 except:

| Area | Setting |
|---|---|
| Embedding model | `BAAI/bge-small-en-v1.5` (384-dim, normalized), query instruction prefix on questions |
| Index contents | 1,921 chunks (unchanged): thinkpython2.pdf 742 · thinkstats2.pdf 636 · thinkbayes.pdf 543 |

### Results

```
Retrieval — by page:    Hit Rate: 77.78%   MRR: 0.648
           by content: Hit Rate: 44.44%   MRR: 0.389
Generation — Answer accuracy: 55.56% (run 1), 66.67% (run 2)
```

| Question | Expected p. | Retrieved pages | Page | Content | Answer run 1 | Answer run 2 | vs Entry 1 (page / content) |
|---|---|---|---|---|---|---|---|
| What is a variable in Python? | 31 | 36, 31, 101, 29 | HIT @2 | HIT @2 | PASS | PASS | better (@4 → @2) / better |
| What is a function in Python? | 39 | 47, 40, 39, 48 | HIT @3 | HIT @1 | PASS | PASS | worse (@1 → @3) / same |
| What is recursion? | 65 | 86, 66, 15, 67 | MISS | MISS | FAIL | PASS | same / same |
| What does a for loop do in Python? | 52 | 87, 206, 86, 206 | MISS | MISS | FAIL | FAIL | same / same |
| What does a while loop do in Python? | 86 | 86, 87, 88, 88 | HIT @1 | MISS | FAIL | PASS | **fixed** / **lost** (was @1) |
| What is a string in Python? | 93 | 93, 29, 99, 111 | HIT @1 | HIT @1 | PASS | PASS | **fixed** / **fixed** |
| What is a list in Python? | 111 | 111, 122, 125, 101 | HIT @1 | MISS | PASS | PASS | same / same |
| What is a tuple in Python? | 137 | 137, 137, 145, 144 | HIT @1 | HIT @1 | FAIL | FAIL | same / better (@2 → @1) |
| What is a dictionary in Python? | 125 | 125, 134, 101, 208 | HIT @1 | MISS | PASS | FAIL | same / same |

### Is it better than MiniLM?

**Retrieval: yes, clearly.** Page Hit Rate rose from 55.6% to 77.8% (+2 questions)
and page MRR from 0.472 to 0.648. Content Hit Rate is flat at 44.4%, but content
MRR rose from 0.306 to 0.389, because correct chunks now rank higher. Similarity
scores are also more confident (top tuple chunk: 72.4% → 82.3%). The "string"
question went from a full miss to rank 1 on both checks. One regression: "while
loop" now finds the right page but not the chunk with the defining sentence.

**Answer accuracy: no measurable change; the drop is noise.** The two runs on the
same index scored 55.56% and 66.67%, with different questions failing each time
(recursion FAIL→PASS, while loop FAIL→PASS, dictionary PASS→FAIL). Entry 1 was a
single run, and the README already records 67–89% for it. The 1.5B model's
randomness hides any retrieval effect. Generation needs to be made deterministic
(temperature 0 and a fixed seed) before its scores can be compared between entries.
Some failures are also keyword false negatives: the tuple answer says "sequence
of **elements**", copied from the book's own glossary, and so misses `values`.

**Verdict:** keep BGE. It's a real retrieval improvement at no extra cost.

### Reference questions (with full chunks)

All answers and chunks below come from one `ask()` call per question.

#### Q1. "What is a tuple in Python?"

**Answer**

> A tuple in Python is an immutable sequence of elements. It is a sequence of
> elements enclosed in parentheses and is a built-in type that is similar to lists
> but is immutable. Tuples can hold elements of different types and are indexed by
> integers.

| Rank | Source | Page | Similarity | Distance | Chunk length |
|---|---|---|---|---|---|
| 1 | thinkpython2.pdf | 137 | 82.3% | 0.177 | 800 chars |
| 2 | thinkpython2.pdf | 137 | 81.1% | 0.189 | 551 chars |
| 3 | thinkpython2.pdf | 145 | 76.6% | 0.234 | 800 chars |
| 4 | thinkpython2.pdf | 144 | 74.4% | 0.256 | 655 chars |

**Chunk 1: thinkpython2.pdf p.137 (82.3%)** (Chapter 12 opening, contains the definition)

```text
Chapter 12
T uples
This chapter presents one more built-in type, the tuple, and then shows how lists, dictionar-
ies, and tuples work together. I also present a useful feature for variable-length argument
lists, the gather and scatter operators.
One note: there is no consensus on how to pronounce “tuple”. Some people say “tuh-
ple”, which rhymes with “supple”. But in the context of programming, most people say
“too-ple”, which rhymes with “quadruple”.
12.1 T uples are immutable
A tuple is a sequence of values. The values can be any type, and they are indexed by
integers, so in that respect tuples are a lot like lists. The important difference is that tuples
are immutable.
Syntactically, a tuple is a comma-separated list of values:
>>> t ='a','b','c','d','e'
Although it is not necessary, it
```

**Chunk 2: thinkpython2.pdf p.137 (81.1%)** (rest of the same page, overlaps chunk 1)

```text
is that tuples
are immutable.
Syntactically, a tuple is a comma-separated list of values:
>>> t ='a','b','c','d','e'
Although it is not necessary, it is common to enclose tuples in parentheses:
>>> t = ('a','b','c','d','e')
To create a tuple with a single element, you have to include a final comma:
>>> t1 ='a',
>>> type(t1)
<class'tuple'>
A value in parentheses is not a tuple:
>>> t2 = ('a')
>>> type(t2)
<class'str'>
Another way to create a tuple is the built-in functiontuple. With no argument, it creates
an empty tuple:
>>> t = tuple()
>>> t
()
```

**Chunk 3: thinkpython2.pdf p.145 (76.6%)** (Chapter 12 glossary and exercises)

```text
12.10. Exercises 123
gather:An operation that collects multiple arguments into a tuple.
scatter:An operation that makes a sequence behave like multiple arguments.
zip object:The result of calling a built-in functionzip; an object that iterates through a
sequence of tuples.
iterator:An object that can iterate through a sequence, but which does not provide list
operators and methods.
data structure:A collection of related values, often organized in lists, dictionaries, tuples,
etc.
shape error:An error caused because a value has the wrong shape; that is, the wrong type
or size.
12.10 Exercises
Exercise 12.1.Write a function calledmost_frequentthat takes a string and prints the let-
ters in decreasing order of frequency. Find text samples from several different languages and see
how letter fr
```

**Chunk 4: thinkpython2.pdf p.144 (74.4%)** (debugging section + glossary start)

```text
8], 9]
>>> structshape(t3)
'list of (3 int, float, 2 str, 2 list of int, int)'
Here’s a list of tuples:
>>> s ='abc'
>>> lt = list(zip(t, s))
>>> structshape(lt)
'list of 3 tuple of (int, str)'
And here’s a dictionary with 3 items that map integers to strings.
>>> d = dict(lt)
>>> structshape(d)
'dict of 3 int->str'
If you are having trouble keeping track of your data structures,structshapecan help.
12.9 Glossary
tuple:An immutable sequence of elements.
tuple assignment:An assignment with a sequence on the right side and a tuple of vari-
ables on the left. The right side is evaluated and then its elements are assigned to the
variables on the left.
```

**Q1 vs Entry 1:** all 4 chunks are still on topic, with higher similarity
(82.3% vs 72.4% at the top). Chunk 4 now brings in the glossary line "tuple: An
immutable sequence of elements", which the answer copies. That's grounded, but it
fails the `values` keyword. Chunks 1 and 2 overlap heavily, so one slot is partly
wasted.

#### Q2. "What is recursion?"

**Answer**

> Recursion is a method of solving a problem where the solution to the problem
> depends on solutions to smaller instances of the same problem.

| Rank | Source | Page | Similarity | Distance | Chunk length |
|---|---|---|---|---|---|
| 1 | thinkpython2.pdf | 86 | 74.3% | 0.257 | 323 chars |
| 2 | thinkpython2.pdf | 66 | 73.0% | 0.270 | 670 chars |
| 3 | thinkpython2.pdf | 15 | 72.8% | 0.272 | 799 chars |
| 4 | thinkpython2.pdf | 67 | 72.5% | 0.275 | 800 chars |

**Chunk 1: thinkpython2.pdf p.86 (74.3%)** (Chapter 7 intro, mentions recursion in passing)

```text
lready seen two functions,countdownandprint_n, that iterate using recursion.
Because iteration is so common, Python provides language features to make it easier. One
is theforstatement we saw in Section 4.2. We’ll get back to that later.
Another is thewhilestatement. Here is a version ofcountdownthat uses awhilestatement:
```

**Chunk 2: thinkpython2.pdf p.66 (73.0%)** (base case, start of infinite recursion)

```text
it.
The fourcountdownframes have different values for the parametern. The bottom of the
stack, wheren=0, is called thebase case. It does not make a recursive call, so there are no
more frames.
As an exercise, draw a stack diagram forprint_ncalled withs ='Hello'andn=2. Then
write a function calleddo_nthat takes a function object and a number,n, as arguments, and
that calls the given functionntimes.
5.10 Infinite recursion
If a recursion never reaches a base case, it goes on making recursive calls forever, and the
program never terminates. This is known asinfinite recursion, and it is generally not a
good idea. Here is a minimal program with an infinite recursion:
```

**Chunk 3: thinkpython2.pdf p.15 (72.8%)** (table of contents)

```text
. . . . . . . . . . . 42
5.8 Recursion . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 43
5.9 Stack diagrams for recursive functions . . . . . . . . . . . . . . . . . . . . . 44
5.10 Infinite recursion . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 44
5.11 Keyboard input . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 45
5.12 Debugging . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 46
5.13 Glossary . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 47
5.14 Exercises . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 47
6 Fruitful functions 51
6.1 Return values . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 51
6.2 Incremental
```

**Chunk 4: thinkpython2.pdf p.67 (72.5%)** (infinite recursion section, same chunk as Entry 1)

```text
5.11. Keyboard input 45
def recurse():
recurse()
In most programming environments, a program with infinite recursion does not really run
forever. Python reports an error message when the maximum recursion depth is reached:
File "<stdin>", line 2, in recurse
File "<stdin>", line 2, in recurse
File "<stdin>", line 2, in recurse
.
.
.
File "<stdin>", line 2, in recurse
RuntimeError: Maximum recursion depth exceeded
This traceback is a little bigger than the one we saw in the previous chapter. When the error
occurs, there are 1000recurseframes on the stack!
If you encounter an infinite recursion by accident, review your function to confirm that
there is a base case that does not make a recursive call. And if there is a base case, check
whether you are guaranteed to reach it.
5.11 Keyboard inpu
```

**Q2 vs Entry 1:** this question got **worse** for grounding.

- The 40-char footer chunk is gone (good). But the glossary chunk from p.69, the
  only chunk in Entry 1 that *defined* recursion, also dropped out of the top 4,
  and the **table of contents** (p.15) took its place.
- The defining page (p.65) is still missed. All four scores are within 2 points
  of each other (72.5–74.3%), so the embedding can't tell "mentions recursion"
  apart from "defines recursion".
- **The answer isn't grounded in any chunk.** "Smaller instances of the same
  problem" is a textbook definition from the model's own training, not from
  Think Python. The prompt says to answer only from context, and the 1.5B model
  ignores that.

### Observations

- Better embeddings fixed the *ranking* problems (string, variable, while-loop
  page) but not the *chunk quality* problems: the table of contents, glossary
  fragments, overlapping duplicates (137 ×2, 206 ×2, 88 ×2) and mid-word cuts all
  still take up slots.
- Most likely next wins, in order:
  1. Make generation deterministic (Ollama `temperature: 0`, fixed `seed`), so
     answer accuracy can be compared between entries.
  2. Ingestion cleanup: skip front matter and table-of-contents pages, strip
     running headers and footers, and drop chunks under ~100 chars.
  3. Remove duplicate pages from the top-k (or retrieve 10 and keep the best chunk
     per page).
  4. Cross-encoder re-ranking, to separate "defines X" from "mentions X".

---

## Entry 1: Baseline (2026-11-25)

### Config snapshot

| Area | Setting |
|---|---|
| Commit | `865bb38` |
| Python / key libs | Python 3.12.15 · chromadb 0.5.23 · sentence-transformers 3.3.1 · pypdf 5.6.0 · anthropic 0.40.0 · fastapi 0.143.5 |
| Ingestion | pypdf `extract_text()`, one record per page, page = PDF index (1-based), **not** the printed page label |
| Chunking | Fixed 800-char sliding window, 150-char overlap, per page (chunks never cross pages, cut mid-word) |
| Embedding model | `all-MiniLM-L6-v2` (384-dim, unit-normalized) |
| Vector store | Chroma, `hnsw:space = cosine` |
| Retrieval | Pure vector search, `TOP_K = 4`, no re-ranking, no similarity threshold, no book filter |
| Generation backend | Ollama `qwen2.5:1.5b` (Q4_K_M, digest `65ec06548149`), no `ANTHROPIC_API_KEY` |
| Prompt | System prompt in [src/generator.py](../src/generator.py): answer only from context, say "don't know", cite "(p. N)". Free-text output |
| Index contents | 1,921 chunks: thinkpython2.pdf 742 · thinkstats2.pdf 636 · thinkbayes.pdf 543 |
| Golden set | 9 Think Python questions ([src/eval_data.py](../src/eval_data.py)) |

### Results

```
Retrieval — by page:    Hit Rate: 55.56%   MRR: 0.472
           by content: Hit Rate: 44.44%   MRR: 0.306
Generation — Answer accuracy: 77.78%
```

| Question | Expected p. | Retrieved pages | Page | Content | Answer |
|---|---|---|---|---|---|
| What is a variable in Python? | 31 | 86, 36, 170, 31 | HIT @4 | HIT @4 | PASS |
| What is a function in Python? | 39 | 39, 47, 48, 40 | HIT @1 | HIT @1 | PASS |
| What is recursion? | 65 | 69, 72, 85, 67 | MISS | MISS | FAIL |
| What does a for loop do in Python? | 52 | 113, 107, 43, 111 | MISS | MISS | FAIL |
| What does a while loop do in Python? | 86 | 87, 43, 218, 87 | MISS | HIT @1 | PASS |
| What is a string in Python? | 93 | 29, 97, 111, 40 | MISS | MISS | PASS |
| What is a list in Python? | 111 | 111, 120, 111, 206 | HIT @1 | MISS | PASS |
| What is a tuple in Python? | 137 | 137, 137, 142, 138 | HIT @1 | HIT @2 | PASS |
| What is a dictionary in Python? | 125 | 125, 134, 227, 210 | HIT @1 | MISS | PASS |

### Reference questions

**Q1. "What is a tuple in Python?"** (retrieval works)

> In Python, a tuple is an immutable sequence of values, much like a list. Each
> tuple is a comma-separated list of values. It is syntactically represented as a
> list of values enclosed in parentheses. However, unlike lists, tuples cannot be
> changed once created. This distinction between immutable and mutable types is
> crucial, as it ensures that tuples maintain their identity over time without
> modification.

| Source | Page | Similarity | Distance |
|---|---|---|---|
| thinkpython2.pdf | 137 | 72.4% | 0.276 |
| thinkpython2.pdf | 137 | 70.1% | 0.299 |
| thinkpython2.pdf | 142 | 65.1% | 0.349 |
| thinkpython2.pdf | 138 | 60.6% | 0.394 |

**Q2. "What is recursion?"** (retrieval misses the defining page, 65)

> Recursion is the process of calling the function that is currently executing.

| Source | Page | Similarity | Distance |
|---|---|---|---|
| thinkpython2.pdf | 69 | 61.6% | 0.384 |
| thinkpython2.pdf | 72 | 59.3% | 0.407 |
| thinkpython2.pdf | 85 | 56.5% | 0.435 |
| thinkpython2.pdf | 67 | 55.3% | 0.447 |

### Full retrieval trace: "What is recursion?"

Everything the model saw for one question: the answer, the source list, and the
full text of the top 4 chunks exactly as stored in Chroma, all from **one**
`ask()` call. (This answer differs from the one under Q2 above. The local model
is non-deterministic, which is why the trace records answer and context from the
same run.)

**Answer**

> Recursion is a process where a function calls itself repeatedly until it
> reaches a base case. The base case is a condition that stops the recursion,
> while the recursive case continues to call itself with a smaller problem until
> the base case is reached.

**Sources**

| Rank | Source | Page | Similarity | Distance | Chunk length |
|---|---|---|---|---|---|
| 1 | thinkpython2.pdf | 69 | 61.6% | 0.384 | 800 chars |
| 2 | thinkpython2.pdf | 72 | 59.3% | 0.407 | 40 chars |
| 3 | thinkpython2.pdf | 85 | 56.5% | 0.435 | 800 chars |
| 4 | thinkpython2.pdf | 67 | 55.3% | 0.447 | 800 chars |

**Chunk 1: thinkpython2.pdf p.69 (61.6%)** (Chapter 5 glossary)

```text
.
condition:The boolean expression in a conditional statement that determines which
branch runs.
compound statement:A statement that consists of a header and a body. The header ends
with a colon (:). The body is indented relative to the header.
branch:One of the alternative sequences of statements in a conditional statement.
chained conditional:A conditional statement with a series of alternative branches.
nested conditional:A conditional statement that appears in one of the branches of another
conditional statement.
return statement:A statement that causes a function to end immediately and return to the
caller.
recursion:The process of calling the function that is currently executing.
base case:A conditional branch in a recursive function that does not make a recursive call.
infinite recu
```

**Chunk 2: thinkpython2.pdf p.72 (59.3%)** (page footer only)

```text
50 Chapter 5. Conditionals and recursion
```

**Chunk 3: thinkpython2.pdf p.85 (56.5%)** (start of Chapter 7, Iteration)

```text
Chapter 7
Iteration
This chapter is about iteration, which is the ability to run a block of statements repeatedly.
We saw a kind of iteration, using recursion, in Section 5.8. We saw another kind, using a
forloop, in Section 4.2. In this chapter we’ll see yet another kind, using awhilestatement.
But first I want to say a little more about variable assignment.
7.1 Reassignment
As you may have discovered, it is legal to make more than one assignment to the same
variable. A new assignment makes an existing variable refer to a new value (and stop
referring to the old value).
>>> x = 5
>>> x
5
>>> x = 7
>>> x
7
The first time we displayx, its value is 5; the second time, its value is 7.
Figure 7.1 shows whatreassignmentlooks like in a state diagram.
At this point I want to address a common sour
```

**Chunk 4: thinkpython2.pdf p.67 (55.3%)** (infinite recursion section)

```text
5.11. Keyboard input 45
def recurse():
recurse()
In most programming environments, a program with infinite recursion does not really run
forever. Python reports an error message when the maximum recursion depth is reached:
File "<stdin>", line 2, in recurse
File "<stdin>", line 2, in recurse
File "<stdin>", line 2, in recurse
.
.
.
File "<stdin>", line 2, in recurse
RuntimeError: Maximum recursion depth exceeded
This traceback is a little bigger than the one we saw in the previous chapter. When the error
occurs, there are 1000recurseframes on the stack!
If you encounter an infinite recursion by accident, review your function to confirm that
there is a base case that does not make a recursive call. And if there is a base case, check
whether you are guaranteed to reach it.
5.11 Keyboard inpu
```

**What the trace shows**

- Only chunk 1 contains a definition, and it's the glossary entry rather than
  the explanation on p.65. The answer's "calls itself" and "base case" are
  grounded in chunk 1. "Repeatedly" and "with a smaller problem" are **not in
  any chunk**: the model added them from its own knowledge.
- **Chunk 2 is junk.** A 40-character page footer scores 59.3% because it contains
  the word "recursion", and it takes up a full context slot. Very short chunks
  (headers and footers) should be filtered out at ingestion.
- **Chunk 3 only mentions recursion in passing.** It's mostly about reassignment.
- **Chunks are cut mid-word**: chunk 1 starts with a stray "." and ends with
  "infinite recu", and chunk 4 ends with "Keyboard inpu". This comes from the
  fixed 800-character window.
- **pypdf drops spaces around code-font words**: "forloop", "awhilestatement",
  "displayx", "1000recurseframes". This hurts both embedding quality and
  keyword or BM25 matching.
- **Running headers are inside chunks** ("5.11. Keyboard input 45" at the top
  of chunk 4).

To reproduce a trace (`main.py ask` doesn't print chunk text):

```bash
python -c "
from src.pipeline import ask
r = ask('What is recursion?')
print(r['answer'])
for i, c in enumerate(r['sources'], 1):
    print(f\"\n--- {i}. {c['source']} p.{c['page']} ({c['similarity']}%) ---\n{c['text']}\")
"
```

### Observations

- **No answer cites a page**, even though the prompt asks for "(p. N)". The 1.5B
  model ignores the instruction, so the app can't show which source backs which claim.
- **The Q2 answer is correct but scored FAIL**: it paraphrases "calls itself" as
  "calling the function that is currently executing". The keyword check has false
  negatives, so the true answer accuracy is likely higher than 77.78%.
- **"for loop" retrieves the wrong chapters** (pp. 107–113, the list/string
  traversal chapters). Short definitional questions match pages that *use* the
  concept rather than the one that *defines* it. Re-ranking should help here.
- **Duplicate pages in the top 4** (137 ×2, 111 ×2, 87 ×2) waste context slots
  because overlapping chunks from one page crowd out other pages.
- **Content misses alongside page hits** (list, dictionary): the right page is
  found, but not the chunk with the defining sentence. This points to the 800-char
  mid-word chunk boundaries.
- Adding thinkbayes.pdf to the index did not change any score compared with the
  Think Python + Think Stats baseline in the README.

---

## Entry template

```markdown
## Entry N: <short change name> (YYYY-MM-DD)

### What changed
- ...

### Config snapshot
(copy the previous table and edit only the rows that changed)

### Results
(paste `python main.py evaluate` output, then the per-question table)

### Reference questions
(Q1 and Q2 answers + source tables)

### Observations
- Better / worse / same, and why
```
