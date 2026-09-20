"""Nuxeo REST adapter — Dublin Core properties only. Never touches file:content."""
from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
from typing import Any
from urllib.parse import urljoin

from app.config import settings
from app.logger import logger

# dc:nature and dc:subjects are Nuxeo vocabularies. Do not send free-text type or keywords.


class NuxeoError(Exception):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def nuxeo_configured() -> bool:
    return bool(settings.nuxeo_url and settings.nuxeo_username and settings.nuxeo_password)


def default_nuxeo_document_id() -> str:
    return (settings.nuxeo_document_id or "").strip()


def properties_from_prototype(record: dict[str, Any]) -> dict[str, Any]:
    """Map validated prototype metadata to standard Nuxeo dublincore fields."""
    metadata = record.get("metadata") or {}
    title = _clean(metadata.get("title"))
    organisation = _clean(metadata.get("organisation"))
    date = _clean(metadata.get("date"))
    type_label = _clean(record.get("documentTypeLabel")) or _clean(record.get("documentType"))

    properties: dict[str, Any] = {}
    if title:
        properties["dc:title"] = title
    description = _description(title, type_label, organisation, date)
    if description:
        properties["dc:description"] = description
    if organisation:
        properties["dc:source"] = organisation
    return properties


def update_document_metadata(
    document_id: str,
    metadata: dict[str, Any] | None = None,
    *,
    properties: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """PUT Dublin Core properties onto an existing Nuxeo document. Does not create a document."""
    if not nuxeo_configured():
        raise NuxeoError(
            "Nuxeo n’est pas configuré. Définissez NUXEO_URL, NUXEO_USERNAME et NUXEO_PASSWORD."
        )
    uid = (document_id or "").strip()
    if not uid:
        raise NuxeoError("Identifiant Nuxeo manquant.")

    payload_properties = properties if properties is not None else dict(metadata or {})
    if not payload_properties:
        raise NuxeoError("Aucune métadonnée compatible à envoyer vers Nuxeo.")

    body = {
        "entity-type": "document",
        "uid": uid,
        "properties": payload_properties,
    }
    url = urljoin(settings.nuxeo_url.rstrip("/") + "/", f"api/v1/id/{uid}")
    timeout = settings.nuxeo_timeout_seconds
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        method="PUT",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": _basic_auth_header(),
        },
    )
    logger.info("nuxeo_put", document_id=uid, fields=sorted(payload_properties.keys()))
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
            status = getattr(response, "status", 200)
    except urllib.error.HTTPError as exc:
        detail = _http_error_message(exc)
        logger.warning("nuxeo_http_error", document_id=uid, status=exc.code, message=detail)
        raise NuxeoError(detail, status_code=exc.code) from None
    except urllib.error.URLError as exc:
        detail = _unreachable_message(exc)
        logger.warning("nuxeo_unreachable", document_id=uid, error=detail)
        raise NuxeoError(detail) from None
    except OSError as exc:
        detail = _unreachable_message(exc)
        logger.warning("nuxeo_unreachable", document_id=uid, error=detail)
        raise NuxeoError(detail) from None
    except TimeoutError:
        raise NuxeoError(
            "Délai dépassé : FastAPI n’a pas obtenu de réponse de Nuxeo."
        ) from None

    return {
        "success": True,
        "document_id": uid,
        "status_code": status,
        "properties": payload_properties,
        "nuxeo_response": _safe_json(raw),
    }


def _description(title: str, type_label: str, organisation: str, date: str) -> str:
    parts = [part for part in (type_label, organisation, date) if part]
    summary = " – ".join(parts)
    if title and summary and title != summary:
        return f"{title}. {summary}."
    if title:
        return title
    return summary


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _basic_auth_header() -> str:
    token = base64.b64encode(
        f"{settings.nuxeo_username}:{settings.nuxeo_password}".encode("utf-8")
    ).decode("ascii")
    return f"Basic {token}"


def _unreachable_message(exc: BaseException) -> str:
    reason = getattr(exc, "reason", exc)
    errno = getattr(reason, "errno", getattr(exc, "errno", None))
    text = str(reason or exc)
    if errno in {113, 10051, 10060, 10061, 10065} or "No route to host" in text or "10061" in text:
        return (
            "FastAPI n’arrive pas à joindre Nuxeo (réseau ou VM). "
            "Vérifiez NUXEO_URL et que la VM est allumée sur le port 8080."
        )
    return (
        "FastAPI n’arrive pas à joindre Nuxeo (réseau ou VM). "
        "Vérifiez NUXEO_URL et que l’instance est démarrée."
    )


def _http_error_message(exc: urllib.error.HTTPError) -> str:
    body = ""
    try:
        body = exc.read().decode("utf-8", errors="replace")
    except Exception:
        body = ""
    parsed = _safe_json(body)
    if exc.code == 401:
        return "Authentification Nuxeo refusée. Vérifiez NUXEO_USERNAME et NUXEO_PASSWORD."
    if exc.code == 404:
        return "Document Nuxeo introuvable. Vérifiez l’UID."
    if exc.code in {403, 405}:
        return "Nuxeo a refusé la mise à jour des propriétés du document."
    if exc.code == 422:
        return _property_update_message(parsed, body)
    if isinstance(parsed, dict):
        for key in ("message", "error", "detail"):
            value = parsed.get(key)
            if isinstance(value, str) and value.strip():
                return _public_nuxeo_message(exc.code, value.strip())
    return _public_nuxeo_message(exc.code, body or exc.reason or "erreur HTTP")


def _property_update_message(parsed: Any, body: str) -> str:
    if isinstance(parsed, dict) and parsed.get("entity-type") == "validation_report":
        parts: list[str] = []
        for violation in parsed.get("violations") or []:
            if not isinstance(violation, dict):
                continue
            message = _clean(violation.get("message"))
            if message:
                parts.append(message)
        if parts:
            compact = " ; ".join(parts)
            if len(compact) > 240:
                compact = compact[:237] + "…"
            return f"Nuxeo a refusé la mise à jour des propriétés : {compact}"
    return _public_nuxeo_message(422, body or "contrainte de schéma")


def _public_nuxeo_message(status: int, detail: str) -> str:
    compact = " ".join(detail.split())
    if len(compact) > 240:
        compact = compact[:237] + "…"
    return f"Nuxeo a renvoyé une erreur HTTP {status}: {compact}"


def _safe_json(raw: str) -> Any:
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None
