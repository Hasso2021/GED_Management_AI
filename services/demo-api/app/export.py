"""Structured JSON ready for a future Nuxeo adapter."""
from __future__ import annotations

from typing import Any

from app.fields import missing, public_field
from app.nuxeo import nuxeo_configured


def build_structured_result(record: dict[str, Any]) -> dict[str, Any]:
    fields = record.get("metadataFields") or {}
    detected = record.get("detectedInformation") or {}
    ai = record.get("aiInformation") or {}
    type_field = {
        "value": record.get("documentType"),
        "source": record.get("documentTypeSource") or "deterministic_rule",
    }
    if record.get("confidence") is not None:
        type_field["confidence"] = record["confidence"]
    if record.get("suggestedDocumentType"):
        type_field["rejected_candidate"] = {
            "value": record["suggestedDocumentType"],
            "label": record.get("suggestedDocumentTypeLabel"),
        }

    personal_types = {str(e.get("type")) for e in (detected.get("entities") or [])}
    address_field = fields.get("address")
    iban_field = fields.get("iban")
    if "address" in personal_types:
        address_field = missing()
    if "iban" in personal_types:
        iban_field = missing()

    return {
        "id": record.get("id"),
        "document": {
            "file_name": record.get("filename"),
            "file_type": record.get("mimeType"),
            "text_extraction_method": record.get("textExtractionMethod"),
            "document_type": type_field,
            "title": public_field(fields.get("title")),
            "document_date": public_field(fields.get("date")),
            "keywords": public_field(fields.get("keywords")),
        },
        "business_metadata": {
            "organization": public_field(fields.get("organisation")),
            "invoice_number": public_field(fields.get("invoiceNumber")),
            "amount": public_field(fields.get("amount")),
            "siret": public_field(fields.get("siret")),
            "vat_number": public_field(fields.get("vatNumber")),
            "address": public_field(address_field),
            "iban": public_field(iban_field),
        },
        "personal_data": {
            "contains_potential_personal_data": bool(
                detected.get("containsPotentialPersonalData")
            ),
            "categories": detected.get("categories") or [],
            "entities": detected.get("entities") or [],
        },
        "ai_information": {
            "ai_generated": True,
            "validation_status": ai.get("validationStatus")
            or _status_from_record(record),
        },
        "nuxeo": {
            "enabled": nuxeo_configured(),
            "properties": {
                "dc:title": "title",
                "dc:description": "title + type + organisation + date",
                "dc:source": "organisation",
            },
            "note": "Seul le schéma Dublin Core compatible est mis à jour. dc:subjects n’est pas envoyé (vocabulaire l10nsubjects). file:content n’est pas modifié.",
        },
    }


def _status_from_record(record: dict[str, Any]) -> str:
    status = record.get("status")
    if status == "validated":
        return "validated"
    if status == "rejected":
        return "rejected"
    if status in {"analyzed", "processing"}:
        return "pending"
    return "pending"
