"""Native PDF text extraction and a simple usability check.

Born-digital PDFs are read with PyMuPDF. Scanned PDFs fall back to Tesseract
in the caller. This module never runs OCR.
"""
from __future__ import annotations

import re

from app.logger import logger

# Thesis-explainable thresholds: enough letters to be real prose, not empty/garbage.
MIN_NON_WHITESPACE_CHARS = 80
MIN_LETTER_RATIO = 0.30

METHOD_PLAIN = "plain_text"
METHOD_NATIVE = "native_pdf_text"
METHOD_OCR = "tesseract_ocr"


def extract_native_pdf_text(pdf_bytes: bytes) -> str:
    """Extract UTF-8 text from every page, keeping line breaks."""
    import fitz

    document = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        pages: list[str] = []
        for page in document:
            pages.append(page.get_text("text") or "")
        combined = "\n\n".join(pages)
        return combined.replace("\x00", "")
    finally:
        document.close()


def is_usable_native_text(text: str) -> bool:
    """True when native PDF text looks substantial enough to skip OCR.

    Rule: at least MIN_NON_WHITESPACE_CHARS characters after stripping
    whitespace, and at least MIN_LETTER_RATIO of those characters are letters.
    """
    compact = re.sub(r"\s+", "", text or "")
    if len(compact) < MIN_NON_WHITESPACE_CHARS:
        logger.info(
            "pdf_native_text_insufficient",
            non_whitespace=len(compact),
            threshold=MIN_NON_WHITESPACE_CHARS,
        )
        return False
    letters = sum(1 for char in compact if char.isalpha())
    ratio = letters / len(compact)
    usable = ratio >= MIN_LETTER_RATIO
    logger.info(
        "pdf_native_text_scored",
        non_whitespace=len(compact),
        letter_ratio=round(ratio, 3),
        usable=usable,
    )
    return usable
