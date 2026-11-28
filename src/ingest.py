"""Step 1: Ingestion. Load textbook PDFs and extract raw text, one record per page.

Text is extracted with pypdfium2 (bindings to PDFium, Chrome's PDF engine). PDFs
rarely store space characters; the extractor has to infer word gaps from glyph
positions. PDFium does this from each character's position on the page, so words
printed in a different font (e.g. code-font `list`) keep their spaces. pypdf
glued them together ("alistis a sequence"), which hurt both embeddings and the
evaluation's exact-phrase check.
"""

import re
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional

import pypdfium2 as pdfium

# PDFium marks a word hyphenated across a line break with U+FFFE and already drops
# the line break itself ("Cre￾ative"), so removing the marker rejoins the word.
_SOFT_HYPHEN = "￾"
# Private-use code points: fragments of large brackets/math symbols, not text.
_PRIVATE_USE = re.compile("[-]")
# Some LaTeX PDFs (e.g. Think Bayes) embed fonts without a Unicode mapping, so
# ligatures, quotes and dashes come out as raw TeX T1-encoding control codes
# ("di\x1ecult" = "difficult"). Control characters never occur in real text,
# so translating them is safe.
_TEX_CONTROL_CODES = str.maketrans({
    "\x10": "“", "\x11": "”",   # “ ”
    "\x15": "–", "\x16": "—",   # – —
    "\x1b": "ff", "\x1c": "fi", "\x1d": "fl", "\x1e": "ffi", "\x1f": "ffl",
    "\x88": "•",                     # • (bullet)
    "\x12": "(", "\x13": ")",             # large math parentheses
})
_OTHER_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")

# --- Page cleanup: keep only body text worth retrieving ---------------------
# Book layouts like these (LaTeX) print a running header as each page's FIRST
# line. It repeats the chapter/section title and page number, so it adds noise
# to every chunk ("116 Chapter 12. Tuples") and no information.
_ROMAN = r"[ivxlc]+"
_PAGE_NO = rf"(?:\d+|{_ROMAN})"
_RUNNING_HEADER = re.compile(
    rf"^(?:"
    rf"{_PAGE_NO} (?:Chapter|Appendix) \S.*"            # "20 Chapter 3. Functions", "194 Appendix A. Debugging"
    rf"|(?:\d+|[A-Z])(?:\.\d+)*\. \S.* {_PAGE_NO}"      # "3.6. Flow of execution 21", "A.2. Runtime errors 195"
    rf"|{_PAGE_NO} (?:Preface|Contents|Index)"          # "xii Preface", "212 Index"
    rf"|(?:Preface|Contents|Index) {_PAGE_NO}"          # "Contents xv", "Index 213"
    rf"|{_ROMAN}"                                       # bare roman page number ("vii")
    rf")$"
)
# Pages of the table of contents or the index: lists of titles and page numbers
# that match many queries ("5.8 Recursion . . . 43") but answer none.
_NON_CONTENT_HEADER = re.compile(rf"^(?:{_PAGE_NO} )?(?:Contents|Index)(?: {_PAGE_NO})?$")
# Fallback for PDFs without those headers: a TOC page is full of dot leaders.
_DOT_LEADER = re.compile(r"(?:\. ){5,}")
_MIN_DOT_LEADER_LINES = 5
# A page left with less text than this after header removal is a blank or
# header-only page (e.g. "50 Chapter 5. Conditionals and recursion" alone).
MIN_PAGE_CHARS = 50


def load_pdfs(data_dir: Path) -> List[Dict]:
    """Extract text from every PDF in data_dir.

    Returns a list of {"text", "source", "page"} records, one per non-empty page.
    Keeping the page number here is what lets later answers cite a page.
    """
    pdf_files = sorted(data_dir.glob("*.pdf"))
    if not pdf_files:
        raise FileNotFoundError(
            f"No PDF files found in {data_dir}. Add a textbook PDF there and try again."
        )

    pages: List[Dict] = []
    for pdf_path in pdf_files:
        pages.extend(load_pdf(pdf_path))
    return pages


def _clean(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace(_SOFT_HYPHEN, "").translate(_TEX_CONTROL_CODES)
    text = _OTHER_CONTROL.sub("", text)
    return _PRIVATE_USE.sub("", text).strip()


def _first_outline_page(pdf: pdfium.PdfDocument) -> Optional[int]:
    """1-based page of the first bookmark (e.g. the Preface), or None if the PDF has no outline.

    Pages before it are the title and copyright pages.
    """
    pages = [
        bookmark.get_dest().get_index() + 1
        for bookmark in pdf.get_toc()
        if bookmark.get_dest() is not None and bookmark.get_dest().get_index() is not None
    ]
    return min(pages) if pages else None


def _skip_reason(page_no: int, text: str, first_content_page: Optional[int]) -> Optional[str]:
    """Why this page should not be indexed, or None to keep it."""
    if first_content_page is not None and page_no < first_content_page:
        return "front matter"
    if _NON_CONTENT_HEADER.match(text.split("\n", 1)[0]):
        return "contents/index"
    if sum(bool(_DOT_LEADER.search(line)) for line in text.split("\n")) >= _MIN_DOT_LEADER_LINES:
        return "contents/index"
    return None


def _strip_running_header(text: str) -> str:
    first, _, rest = text.partition("\n")
    return rest.strip() if _RUNNING_HEADER.match(first.strip()) else text


def load_pdf(pdf_path: Path, stats: Optional[Counter] = None) -> List[Dict]:
    """Extract body text from a single PDF, one record per kept page.

    Skips front matter, table-of-contents and index pages, strips each page's
    running header, and drops pages left (nearly) empty. Page numbers stay the
    PDF's own (1-based), so citations still point at the right page. Pass a
    Counter as `stats` to see how many pages each rule removed.
    """
    stats = stats if stats is not None else Counter()
    pdf = pdfium.PdfDocument(str(pdf_path))
    pages: List[Dict] = []
    try:
        first_content_page = _first_outline_page(pdf)
        for index in range(len(pdf)):
            page = pdf[index]
            textpage = page.get_textpage()
            try:
                text = _clean(textpage.get_text_range())
            finally:
                # PDFium objects hold native memory; close them rather than waiting for GC.
                textpage.close()
                page.close()

            page_no = index + 1
            reason = _skip_reason(page_no, text, first_content_page)
            if reason is None:
                text = _strip_running_header(text)
                if text != "" and len(text) < MIN_PAGE_CHARS:
                    reason = "too short"
                elif not text:
                    reason = "empty"
            if reason:
                stats[reason] += 1
                continue
            stats["kept"] += 1
            pages.append({"text": text, "source": pdf_path.name, "page": page_no})
    finally:
        pdf.close()
    return pages
