"""Provenance-aware metadata field helpers.

Confidence is attached only when a real classifier score exists.
"""
from __future__ import annotations

from typing import Any

SOURCE_REGEX = "regex"
SOURCE_SPACY = "spacy_ner"
SOURCE_ML = "ml_classifier"
SOURCE_OCR = "ocr"
SOURCE_FILENAME = "filename"
SOURCE_RULE = "deterministic_rule"
SOURCE_DERIVED = "derived_metadata"
SOURCE_HUMAN = "human_modified"

NOT_DETECTED = "not_detected"


def detected(
    value: Any,
    source: str,
    *,
    confidence: float | None = None,
    validated: bool = False,
    original_value: Any | None = None,
) -> dict[str, Any]:
    field: dict[str, Any] = {
        "value": value,
        "source": source,
        "validated": validated,
    }
    if confidence is not None:
        field["confidence"] = confidence
    if original_value is not None:
        field["original_value"] = original_value
    return field


def missing() -> dict[str, Any]:
    return {"value": None, "status": NOT_DETECTED}


def is_missing(field: dict[str, Any] | None) -> bool:
    if not field:
        return True
    if field.get("status") == NOT_DETECTED:
        return True
    value = field.get("value")
    return value is None or value == ""


def from_optional(value: Any, source: str | None) -> dict[str, Any]:
    if value is None or value == "" or not source:
        return missing()
    return detected(value, source)


def apply_human_edit(field: dict[str, Any] | None, new_value: str) -> dict[str, Any]:
    current = field or missing()
    previous = current.get("value")
    if previous == new_value or (is_missing(current) and new_value == ""):
        return current
    original = current.get("original_value", previous)
    updated = detected(new_value or None, SOURCE_HUMAN, original_value=original)
    if new_value == "":
        return {
            "value": None,
            "status": NOT_DETECTED,
            "source": SOURCE_HUMAN,
            "original_value": original,
            "validated": False,
        }
    return updated


def mark_validated(field: dict[str, Any]) -> dict[str, Any]:
    updated = dict(field)
    if not is_missing(updated):
        updated["validated"] = True
    return updated


def public_field(field: dict[str, Any] | None) -> dict[str, Any]:
    """Shape a field for the structured JSON export."""
    if is_missing(field):
        out: dict[str, Any] = {"value": None, "status": NOT_DETECTED}
        if field and field.get("source") == SOURCE_HUMAN:
            out["source"] = SOURCE_HUMAN
            if "original_value" in field:
                out["original_value"] = field["original_value"]
        return out

    assert field is not None
    out = {"value": field["value"], "source": field["source"]}
    if "confidence" in field:
        out["confidence"] = field["confidence"]
    if "original_value" in field:
        out["original_value"] = field["original_value"]
    out["validated"] = bool(field.get("validated"))
    return out
