"""Filesystem document store — JSON metadata + uploaded files. No MongoDB."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

from app.config import settings

INDEX_NAME = "index.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _root() -> str:
    os.makedirs(settings.data_dir, exist_ok=True)
    return settings.data_dir


def _index_path() -> str:
    return os.path.join(_root(), INDEX_NAME)


def _doc_dir(doc_id: str) -> str:
    path = os.path.join(_root(), "documents", doc_id)
    os.makedirs(path, exist_ok=True)
    return path


def _load_index() -> dict[str, Any]:
    path = _index_path()
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _save_index(index: dict[str, Any]) -> None:
    with open(_index_path(), "w", encoding="utf-8") as fh:
        json.dump(index, fh, ensure_ascii=False, indent=2)


def create_document(
    doc_id: str,
    filename: str,
    mime_type: str,
    file_bytes: bytes,
) -> dict[str, Any]:
    folder = _doc_dir(doc_id)
    ext = os.path.splitext(filename)[1] or ""
    stored_name = f"original{ext}"
    file_path = os.path.join(folder, stored_name)
    with open(file_path, "wb") as fh:
        fh.write(file_bytes)

    record = {
        "id": doc_id,
        "filename": filename,
        "mimeType": mime_type,
        "filePath": file_path,
        "fileSize": len(file_bytes),
        "status": "uploaded",
        "documentType": None,
        "documentTypeLabel": None,
        "confidence": None,
        "classificationMethod": None,
        "ocrText": None,
        "metadata": empty_metadata(),
        "extractedFields": {},
        "metadataFields": {},
        "detectedInformation": {
            "business": [],
            "personal": [],
            "containsPotentialPersonalData": False,
            "categories": [],
            "entities": [],
        },
        "pii": {"present": False, "categories": [], "entities": []},
        "aiInformation": {"aiGenerated": True, "validationStatus": "pending"},
        "originalMetadata": {},
        "documentTypeSource": None,
        "suggestedDocumentType": None,
        "suggestedDocumentTypeLabel": None,
        "textExtractionMethod": None,
        "error": None,
        "createdAt": _now(),
        "updatedAt": _now(),
    }
    index = _load_index()
    index[doc_id] = record
    _save_index(index)
    return record


def empty_metadata() -> dict[str, str]:
    return {
        "title": "",
        "organisation": "",
        "date": "",
        "invoiceNumber": "",
        "amount": "",
        "siret": "",
        "keywords": "",
    }


def get_document(doc_id: str) -> dict[str, Any] | None:
    return _load_index().get(doc_id)


def read_file_bytes(doc_id: str) -> bytes:
    record = get_document(doc_id)
    if record is None:
        raise FileNotFoundError(doc_id)
    with open(record["filePath"], "rb") as fh:
        return fh.read()


def save_text(doc_id: str, name: str, text: str) -> str:
    path = os.path.join(_doc_dir(doc_id), name)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return path


def update_document(doc_id: str, patch: dict[str, Any]) -> dict[str, Any]:
    index = _load_index()
    if doc_id not in index:
        raise KeyError(doc_id)
    index[doc_id].update(patch)
    index[doc_id]["updatedAt"] = _now()
    _save_index(index)
    return index[doc_id]


def public_view(record: dict[str, Any]) -> dict[str, Any]:
    """Strip internal filesystem paths before sending to the UI."""
    view = {k: v for k, v in record.items() if k != "filePath"}
    return view
