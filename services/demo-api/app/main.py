from __future__ import annotations

from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.config import settings
from app.fields import apply_human_edit, mark_validated
from app.logger import configure_logging, logger
from app import export as export_mod
from app import nuxeo as nuxeo_mod
from app import pipeline, store

ALLOWED_MIME = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/tiff",
    "text/plain",
}
MAX_BYTES = 15 * 1024 * 1024


class MetadataPatch(BaseModel):
    title: str | None = None
    organisation: str | None = None
    date: str | None = None
    invoiceNumber: str | None = None
    amount: str | None = None
    siret: str | None = None
    keywords: str | None = None


class NuxeoSendBody(BaseModel):
    nuxeoDocumentId: str | None = None


@asynccontextmanager
async def lifespan(_app: FastAPI):
    configure_logging(settings.log_level)
    store._root()
    pipeline.warmup()
    logger.info("demo_api_starting", port=settings.port)
    yield
    logger.info("demo_api_stopping")


app = FastAPI(title="GED Management AI", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origin.split(",")] if settings.cors_origin != "*" else ["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "demo-api",
        "nuxeo_configured": nuxeo_mod.nuxeo_configured(),
        "nuxeo_url": settings.nuxeo_url or None,
    }


@app.post("/api/documents")
async def upload_document(file: UploadFile = File(...)) -> dict:
    mime = file.content_type or "application/octet-stream"
    if mime not in ALLOWED_MIME:
        raise HTTPException(
            status_code=415,
            detail="Formats acceptés : PDF, PNG, JPEG, TIFF, TXT.",
        )
    data = await file.read()
    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="Fichier trop volumineux (15 Mo max).")
    if not data:
        raise HTTPException(status_code=400, detail="Fichier vide.")

    doc_id = str(uuid4())
    filename = file.filename or "document"
    record = store.create_document(doc_id, filename, mime, data)
    logger.info("document_uploaded", document_id=doc_id, filename=filename)
    return store.public_view(record)


@app.post("/api/documents/{doc_id}/analyze")
def analyze_document(doc_id: str) -> dict:
    record = store.get_document(doc_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Document introuvable.")

    store.update_document(doc_id, {"status": "processing", "error": None})
    try:
        file_bytes = store.read_file_bytes(doc_id)
        result = pipeline.analyze(file_bytes, record["mimeType"], record["filename"])
        store.save_text(doc_id, "ocr.txt", result["ocrText"])
        updated = store.update_document(
            doc_id,
            {
                "status": "analyzed",
                "documentType": result["documentType"],
                "documentTypeLabel": result["documentTypeLabel"],
                "confidence": result["confidence"],
                "classificationMethod": result["classificationMethod"],
                "ocrText": result["ocrText"],
                "extractedFields": result["extractedFields"],
                "metadata": result["metadata"],
                "metadataFields": result["metadataFields"],
                "detectedInformation": result["detectedInformation"],
                "pii": result["pii"],
                "aiInformation": result["aiInformation"],
                "originalMetadata": result["originalMetadata"],
                "documentTypeSource": result["documentTypeSource"],
                "suggestedDocumentType": result.get("suggestedDocumentType"),
                "suggestedDocumentTypeLabel": result.get("suggestedDocumentTypeLabel"),
                "textExtractionMethod": result.get("textExtractionMethod"),
                "error": None,
            },
        )
        logger.info(
            "document_analyzed",
            document_id=doc_id,
            document_type=result["documentType"],
            confidence=result["confidence"],
        )
        return store.public_view(updated)
    except Exception as exc:
        logger.error("analyze_failed", document_id=doc_id, error=str(exc))
        store.update_document(doc_id, {"status": "failed", "error": str(exc)})
        raise HTTPException(status_code=500, detail=f"Analyse impossible : {exc}") from exc


@app.get("/api/documents/{doc_id}")
def get_document(doc_id: str) -> dict:
    record = store.get_document(doc_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Document introuvable.")
    return store.public_view(record)


@app.patch("/api/documents/{doc_id}/metadata")
def update_metadata(doc_id: str, body: MetadataPatch) -> dict:
    record = store.get_document(doc_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Document introuvable.")
    metadata = dict(record.get("metadata") or store.empty_metadata())
    fields = dict(record.get("metadataFields") or {})
    original = dict(record.get("originalMetadata") or metadata)
    for key, value in body.model_dump(exclude_none=True).items():
        metadata[key] = value
        fields[key] = apply_human_edit(fields.get(key), value)
    updated = store.update_document(
        doc_id,
        {
            "metadata": metadata,
            "metadataFields": fields,
            "originalMetadata": original,
        },
    )
    return store.public_view(updated)


@app.post("/api/documents/{doc_id}/validate")
def validate_document(doc_id: str) -> dict:
    record = store.get_document(doc_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Document introuvable.")
    if record.get("status") not in ("analyzed", "validated", "rejected"):
        raise HTTPException(status_code=409, detail="Le document doit d'abord être analysé.")
    fields = {key: mark_validated(value) for key, value in (record.get("metadataFields") or {}).items()}
    ai = dict(record.get("aiInformation") or {"aiGenerated": True})
    ai["validationStatus"] = "validated"
    updated = store.update_document(
        doc_id,
        {"status": "validated", "metadataFields": fields, "aiInformation": ai},
    )
    return store.public_view(updated)


@app.post("/api/documents/{doc_id}/reject")
def reject_document(doc_id: str) -> dict:
    record = store.get_document(doc_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Document introuvable.")
    if record.get("status") not in ("analyzed", "validated", "rejected"):
        raise HTTPException(status_code=409, detail="Le document doit d'abord être analysé.")
    ai = dict(record.get("aiInformation") or {"aiGenerated": True})
    ai["validationStatus"] = "rejected"
    updated = store.update_document(doc_id, {"status": "rejected", "aiInformation": ai})
    return store.public_view(updated)


@app.post("/api/documents/{doc_id}/nuxeo")
def send_to_nuxeo(doc_id: str, body: NuxeoSendBody = NuxeoSendBody()) -> dict:
    record = store.get_document(doc_id)
    if record is None:
        return {"success": False, "message": "Document introuvable."}
    if record.get("status") != "validated":
        return {
            "success": False,
            "message": "Validez d’abord les métadonnées avant de les envoyer vers Nuxeo.",
        }
    nuxeo_id = (body.nuxeoDocumentId or nuxeo_mod.default_nuxeo_document_id()).strip()
    if not nuxeo_id:
        return {
            "success": False,
            "message": "UID Nuxeo manquant. Définissez NUXEO_DOCUMENT_ID.",
        }
    properties = nuxeo_mod.properties_from_prototype(record)
    try:
        result = nuxeo_mod.update_document_metadata(nuxeo_id, properties=properties)
    except nuxeo_mod.NuxeoError as exc:
        store.update_document(
            doc_id,
            {
                "nuxeo": {
                    "success": False,
                    "document_id": nuxeo_id,
                    "message": exc.message,
                }
            },
        )
        logger.warning("nuxeo_send_failed", document_id=doc_id, nuxeo_id=nuxeo_id, error=exc.message)
        return {"success": False, "document_id": nuxeo_id, "message": exc.message}

    message = "Métadonnées envoyées vers Nuxeo"
    store.update_document(
        doc_id,
        {
            "nuxeo": {
                "success": True,
                "document_id": nuxeo_id,
                "message": message,
                "properties": sorted(properties),
            }
        },
    )
    logger.info("nuxeo_send_ok", document_id=doc_id, nuxeo_id=nuxeo_id)
    return {"success": True, "document_id": nuxeo_id, "message": message}


@app.get("/api/documents/{doc_id}/json")
def export_json(doc_id: str) -> dict:
    record = store.get_document(doc_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Document introuvable.")
    return export_mod.build_structured_result(record)
