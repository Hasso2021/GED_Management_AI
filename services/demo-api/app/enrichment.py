"""Deterministic metadata enrichment: title, keywords, display helpers."""
from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.fields import SOURCE_DERIVED, SOURCE_FILENAME
from app.keyword_classifier import looks_like_rib_document

TYPE_LABELS: dict[str, str] = {
    "FACTURE": "Facture",
    "DEVIS": "Devis",
    "KBIS": "Extrait KBIS",
    "URSSAF": "Attestation URSSAF",
    "RIB": "RIB",
    "SIRET_ATTESTATION": "Attestation SIRET",
    "UNKNOWN": "Document inconnu",
}

MONTHS_FR = {
    1: "janvier",
    2: "février",
    3: "mars",
    4: "avril",
    5: "mai",
    6: "juin",
    7: "juillet",
    8: "août",
    9: "septembre",
    10: "octobre",
    11: "novembre",
    12: "décembre",
}

_CONCEPT_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bcr[eè]che", re.IGNORECASE), "crèche"),
    (re.compile(r"\burs+a+f\b", re.IGNORECASE), "URSSAF"),
    (re.compile(r"\bkbis\b", re.IGNORECASE), "KBIS"),
    (re.compile(r"\bdevis\b", re.IGNORECASE), "devis"),
]

_FILENAME_CONCEPTS = {
    "creche": "Crèche",
    "crèche": "Crèche",
    "cmg": "CMG",
    "urssaf": "URSSAF",
    "ursaaf": "URSSAF",
    "ursaff": "URSSAF",
    "kbis": "KBIS",
    "rib": "RIB",
    "caf": "CAF",
}

_ACRONYMS = {
    "SARL",
    "SASU",
    "SAS",
    "EURL",
    "SA",
    "SCI",
    "SELARL",
    "SNC",
    "GIE",
    "LPC",
    "CMG",
    "CAF",
    "RIB",
    "KBIS",
    "RCS",
    "SIRET",
    "TVA",
}

_PERSON_HINT = re.compile(r"\b(M\.|Mme|Mlle|Monsieur|Madame)\s+", re.IGNORECASE)


def _fold(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value.lower())
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


def clean_filename(filename: str) -> str:
    name = filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    if "." in name:
        name = name.rsplit(".", 1)[0]
    name = re.sub(r"[_\-]+", " ", name)
    return re.sub(r"\s+", " ", name).strip()


def period_from_iso(iso_date: str | None) -> str | None:
    if not iso_date or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", iso_date):
        return None
    year, month, _day = iso_date.split("-")
    label = MONTHS_FR.get(int(month))
    if not label:
        return None
    return f"{label} {year}"


def pretty_org(name: str) -> str:
    parts: list[str] = []
    for raw in name.split():
        token = raw.strip(" ,;")
        if not token:
            continue
        upper = token.upper().replace(".", "")
        letters = re.sub(r"[^A-ZÀ-Ÿ]", "", token.upper())
        if upper in _ACRONYMS or (token.isupper() and 2 <= len(letters) <= 8):
            parts.append(token.upper())
        elif any(c.islower() for c in token) and any(c.isupper() for c in token[1:]):
            parts.append(token)
        else:
            parts.append(token.capitalize())
    return " ".join(parts)


def detect_concept(text: str, filename: str, document_type: str = "") -> str | None:
    invoice_like = document_type in {"FACTURE", "DEVIS"}
    if not invoice_like and looks_like_rib_document(text, filename):
        return "RIB"
    blob = f"{filename} {text}"
    for pattern, label in _CONCEPT_PATTERNS:
        if pattern.search(blob):
            return label
    stem = clean_filename(filename).lower()
    for token, label in _FILENAME_CONCEPTS.items():
        if invoice_like and label == "RIB":
            continue
        if re.search(rf"\b{re.escape(token)}\b", stem):
            return label[0].lower() + label[1:] if label != label.upper() else label
    return None


def generate_title(
    filename: str,
    document_type: str,
    entities: dict[str, Any],
    text: str,
) -> tuple[str, str]:
    label = TYPE_LABELS.get(document_type, document_type)
    org = entities.get("companyName") or entities.get("bankName")
    date = (
        entities.get("invoiceDate")
        or entities.get("incorporationDate")
        or entities.get("urssafExpirationDate")
        or entities.get("documentDate")
    )
    concept = detect_concept(text, filename, document_type)
    period = period_from_iso(date) if isinstance(date, str) else None
    if not period:
        raw_period = entities.get("urssafPeriod")
        if raw_period:
            period = str(raw_period)

    if document_type == "UNKNOWN":
        if org and period:
            return f"{pretty_org(str(org))} – {period}", SOURCE_DERIVED
        if org:
            return pretty_org(str(org)), SOURCE_DERIVED
        return clean_filename(filename), SOURCE_FILENAME

    useful_concept = concept and concept.lower() not in label.lower()
    if not org and not period and not useful_concept:
        return clean_filename(filename), SOURCE_FILENAME

    head = label
    if useful_concept:
        head = f"{label} {concept}"

    parts = [head]
    if period:
        parts.append(period)
    if org and str(org).lower() not in head.lower():
        parts.append(pretty_org(str(org)))
    return " – ".join(parts), SOURCE_DERIVED


def generate_keywords(
    filename: str,
    document_type: str,
    entities: dict[str, Any],
    text: str,
) -> tuple[str, str]:
    label = TYPE_LABELS.get(document_type, document_type)
    items: list[str] = [label]

    concept = detect_concept(text, filename, document_type)
    if concept:
        display = concept[0].upper() + concept[1:] if concept[:1].islower() else concept
        if display.lower() not in {label.lower()}:
            items.append(display)

    org = str(entities.get("companyName") or "")
    raw = entities.get("rawEntities") or {}
    for candidate in raw.get("orgs") or []:
        if _useful_brand(str(candidate), org):
            items.append(str(candidate).strip())
            break

    date = (
        entities.get("invoiceDate")
        or entities.get("incorporationDate")
        or entities.get("urssafExpirationDate")
        or entities.get("documentDate")
    )
    period = period_from_iso(date) if isinstance(date, str) else None
    if not period and entities.get("urssafPeriod"):
        period = str(entities["urssafPeriod"])
    if period:
        items.append(period[0].upper() + period[1:] if period[:1].islower() else period)

    stem = clean_filename(filename)
    for token in re.split(r"[\s_\-]+", stem):
        mapped = _FILENAME_CONCEPTS.get(token.lower())
        if mapped and mapped.lower() not in {item.lower() for item in items}:
            items.append(mapped)

    unique = list(dict.fromkeys(item for item in items if item))
    return ", ".join(unique), SOURCE_DERIVED


def _useful_brand(candidate: str, organisation: str) -> bool:
    text = " ".join(candidate.split())
    if len(text) < 4 or len(text) > 60:
        return False
    if re.match(r"^(Mile|Mme|Mlle|M\.|Mr\.?|Monsieur|Madame)\b", text, re.IGNORECASE):
        return False
    if _PERSON_HINT.search(text):
        return False
    folded = _fold(text)
    if re.search(r"\breleve\b", folded) or re.search(
        r"\b(electricite|facture|devis|montant|total|conso|attestation|vigilance)\b",
        folded,
    ):
        return False
    compact = re.sub(r"[^a-z]", "", folded)
    if compact in {
        "realisee",
        "realise",
        "effectuee",
        "emise",
        "page",
        "document",
        "duplicata",
    }:
        return False
    if text.isupper() and not re.search(r"\b(SARL|SAS|BANQUE|BANK|CAISSE)\b", text, re.IGNORECASE):
        return False
    org_norm = organisation.lower().strip()
    cand_norm = text.lower().strip()
    if org_norm and (cand_norm == org_norm or cand_norm in org_norm or org_norm in cand_norm):
        return False
    return True
