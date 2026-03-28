"""
cv_parser.py — Extracts text from a CV/resume PDF.
"""

import pdfplumber


def extract_cv_text(pdf_path: str) -> str:
    """Read a PDF and return all text as a single string."""
    text_parts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    if not text_parts:
        raise ValueError(f"Could not extract text from '{pdf_path}'. Make sure the PDF is not scanned/image-only.")
    return "\n".join(text_parts)
