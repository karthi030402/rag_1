"""Step 1: Ingestion. Load textbook PDFs and extract raw text, one record per page."""

from pathlib import Path
from typing import Dict, List

from pypdf import PdfReader


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
        reader = PdfReader(str(pdf_path))
        for page_num, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").strip()
            if not text:
                continue
            pages.append({"text": text, "source": pdf_path.name, "page": page_num})

    return pages
