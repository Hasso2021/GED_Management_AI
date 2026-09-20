"""In-process pipeline: OCR → classify → extract → metadata enrichment + PII split.

Reuses the existing processing modules without MinIO, MongoDB or Airflow.
"""
from __future__ import annotations

from typing import Any

from app.enrichment import TYPE_LABELS, generate_keywords, generate_title
from app.extractor import extract, load_nlp
from app.fields import SOURCE_ML, SOURCE_REGEX, SOURCE_RULE, detected, from_optional, missing
from app.keyword_classifier import classify_by_keywords, has_distinctive_evidence
from app.ml_classifier import classify_ml_ranked, load_model
from app.logger import logger
from app.ocr_engine import run_ocr
from app.pdf_text import (
    METHOD_NATIVE,
    METHOD_OCR,
    METHOD_PLAIN,
    extract_native_pdf_text,
    is_usable_native_text,
)
from app.pii import detect_information
from app.preprocessor import preprocess
from app.store import empty_metadata

ML_CONFIDENCE_THRESHOLD = 0.6
ML_MARGIN_THRESHOLD = 0.2

METHOD_SOURCE = {
    "ml": SOURCE_ML,
    "keyword": SOURCE_RULE,
    "unknown": SOURCE_RULE,
}


def warmup() -> None:
    load_model()
    load_nlp()


def extract_document_text(file_bytes: bytes, mime_type: str) -> tuple[str, str]:
    """Return (text, text_extraction_method). Tesseract runs only as PDF/image fallback."""
    if mime_type == "text/plain":
        return file_bytes.decode("utf-8", errors="replace"), METHOD_PLAIN

    if mime_type == "application/pdf":
        native = ""
        try:
            native = extract_native_pdf_text(file_bytes)
        except Exception as exc:
            logger.warning("pdf_native_extract_failed", error=str(exc))
        if is_usable_native_text(native):
            logger.info("pdf_text_source", method=METHOD_NATIVE)
            return native, METHOD_NATIVE
        logger.info("pdf_text_source", method=METHOD_OCR)
        return run_ocr(file_bytes, mime_type), METHOD_OCR

    processed = file_bytes
    if mime_type.startswith("image/"):
        try:
            processed = preprocess(file_bytes)
        except Exception:
            processed = file_bytes
    return run_ocr(processed, mime_type), METHOD_OCR


def run_ocr_bytes(file_bytes: bytes, mime_type: str) -> str:
    text, _method = extract_document_text(file_bytes, mime_type)
    return text


def classify_text(text: str, filename: str = "") -> tuple[str, float, str, str | None]:
    """Return (type, confidence, method, rejected_candidate).

    ML is tried first. A class is kept only with a clear probability margin
    and type-specific evidence. Shared footer tokens are not enough.
    Out-of-taxonomy documents fall back to UNKNOWN.
    """
    ml_type: str | None = None
    ml_confidence = 0.0
    ml_margin = 0.0
    try:
        ml_type, ml_confidence, ml_margin = classify_ml_ranked(text)
    except RuntimeError:
        pass

    ml_ranked = (
        ml_type is not None
        and ml_confidence >= ML_CONFIDENCE_THRESHOLD
        and ml_margin >= ML_MARGIN_THRESHOLD
    )
    if ml_ranked and ml_type and has_distinctive_evidence(text, filename, ml_type):
        return ml_type, ml_confidence, "ml", None

    kw_type, kw_confidence = classify_by_keywords(text, filename)
    if kw_type != "UNKNOWN" and has_distinctive_evidence(text, filename, kw_type):
        return kw_type, kw_confidence, "keyword", None

    rejected = ml_type if ml_type and ml_type != "UNKNOWN" else None
    if rejected is None and kw_type != "UNKNOWN":
        rejected = kw_type
    confidence = ml_confidence if ml_type is not None else kw_confidence
    return "UNKNOWN", confidence, "unknown", rejected


def _format_amount(amount: float | int | str, currency: str) -> str:
    try:
        value = float(amount)
    except (TypeError, ValueError):
        return f"{amount} {currency}".strip()
    formatted = f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", " ")
    return f"{formatted} {currency}"


def _flat_value(field: dict[str, Any]) -> str:
    value = field.get("value")
    if value is None:
        return ""
    return str(value)


def build_proposed_metadata(
    filename: str,
    document_type: str,
    entities: dict[str, Any],
    text: str,
) -> tuple[dict[str, str], dict[str, Any]]:
    sources = entities.get("_sources") or {}
    title, title_src = generate_title(filename, document_type, entities, text)
    keywords, keywords_src = generate_keywords(filename, document_type, entities, text)

    org = entities.get("companyName") or entities.get("bankName")
    date = (
        entities.get("invoiceDate")
        or entities.get("incorporationDate")
        or entities.get("urssafExpirationDate")
        or entities.get("urssafPeriod")
        or entities.get("documentDate")
    )
    invoice = entities.get("invoiceNumber")
    amount_raw = entities.get("amountTTC") or entities.get("amountHT")
    amount_src_key = "amountTTC" if entities.get("amountTTC") is not None else "amountHT"
    if amount_raw is None and document_type == "KBIS":
        amount_raw = entities.get("shareCapital")
        amount_src_key = "shareCapital"
    amount = None
    if amount_raw is not None and amount_raw != "":
        amount = _format_amount(amount_raw, str(entities.get("currency") or "EUR"))
        amount_src = sources.get(amount_src_key) or SOURCE_REGEX
    else:
        amount_src = None

    fields = {
        "title": detected(title, title_src),
        "organisation": from_optional(org, sources.get("companyName") or sources.get("bankName")),
        "date": from_optional(
            date,
            sources.get("invoiceDate")
            or sources.get("incorporationDate")
            or sources.get("urssafExpirationDate")
            or sources.get("urssafPeriod")
            or sources.get("documentDate"),
        ),
        "invoiceNumber": from_optional(invoice, sources.get("invoiceNumber")),
        "amount": from_optional(amount, amount_src),
        "siret": from_optional(entities.get("siret"), sources.get("siret")),
        "keywords": detected(keywords, keywords_src) if keywords else missing(),
        "vatNumber": from_optional(entities.get("tvaNumber"), sources.get("tvaNumber")),
        "address": from_optional(entities.get("address"), sources.get("address")),
        "iban": from_optional(entities.get("iban"), sources.get("iban")),
    }

    meta = empty_metadata()
    for key in meta:
        meta[key] = _flat_value(fields[key])
    return meta, fields


def analyze(file_bytes: bytes, mime_type: str, filename: str) -> dict[str, Any]:
    text, text_method = extract_document_text(file_bytes, mime_type)
    document_type, confidence, method, rejected = classify_text(text, filename)
    entities = extract(text, document_type)
    metadata, metadata_fields = build_proposed_metadata(filename, document_type, entities, text)
    detected_info = detect_information(text, entities)
    return {
        "ocrText": text,
        "documentType": document_type,
        "documentTypeLabel": TYPE_LABELS.get(document_type, document_type),
        "documentTypeSource": METHOD_SOURCE.get(method, SOURCE_RULE),
        "confidence": confidence,
        "classificationMethod": method,
        "suggestedDocumentType": rejected,
        "suggestedDocumentTypeLabel": TYPE_LABELS.get(rejected, rejected) if rejected else None,
        "extractedFields": {k: v for k, v in entities.items() if k != "_sources"},
        "metadata": metadata,
        "metadataFields": metadata_fields,
        "detectedInformation": {
            "business": detected_info["business"],
            "personal": detected_info["personal"],
            "containsPotentialPersonalData": detected_info["contains_potential_personal_data"],
            "categories": detected_info["categories"],
            "entities": detected_info["entities"],
        },
        "pii": {
            "present": detected_info["contains_potential_personal_data"],
            "categories": detected_info["categories"],
            "entities": detected_info["entities"],
        },
        "aiInformation": {
            "aiGenerated": True,
            "validationStatus": "pending",
        },
        "originalMetadata": dict(metadata),
        "textExtractionMethod": text_method,
    }
