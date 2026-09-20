"""Tesseract OCR wrapper with PDF multi-page support."""
import io
import pytesseract
from PIL import Image
from app.config import settings
from app.logger import logger


_TESSERACT_CONFIG = "--oem 3 --psm 6"


def _ocr_image_bytes(image_bytes: bytes) -> str:
    img = Image.open(io.BytesIO(image_bytes))
    return pytesseract.image_to_string(img, lang=settings.tesseract_lang, config=_TESSERACT_CONFIG)


def run_ocr(preprocessed_bytes: bytes, mime_type: str, correlation_id: str = "") -> str:
    """
    Run Tesseract OCR.
    - For images: single-pass OCR on the preprocessed bytes.
    - For PDFs: convert each page via PIL (requires pdf2image / poppler) and OCR each page.
    """
    if mime_type == "application/pdf":
        return _ocr_pdf(preprocessed_bytes, correlation_id)
    return _ocr_image_bytes(preprocessed_bytes)


def _ocr_pdf(pdf_bytes: bytes, correlation_id: str) -> str:
    try:
        from pdf2image import convert_from_bytes  # type: ignore
        pages = convert_from_bytes(pdf_bytes, dpi=300)
        texts: list[str] = []
        for i, page in enumerate(pages):
            buf = io.BytesIO()
            page.save(buf, format="PNG")
            text = pytesseract.image_to_string(
                Image.open(io.BytesIO(buf.getvalue())),
                lang=settings.tesseract_lang,
                config=_TESSERACT_CONFIG,
            )
            texts.append(text)
            logger.info("ocr_page_done", page=i + 1, total=len(pages), correlation_id=correlation_id)
        return "\n\n--- PAGE BREAK ---\n\n".join(texts)
    except ImportError:
        logger.warning("pdf2image_not_available_falling_back", correlation_id=correlation_id)
        # Fallback: treat PDF bytes as an image (works for single-page PDFs rendered as images)
        return _ocr_image_bytes(pdf_bytes)
