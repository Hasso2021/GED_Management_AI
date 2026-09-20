"""Separate business identifiers from potential personal data.

Indicative detection only — not a GDPR compliance assessment.
"""
from __future__ import annotations

import re
from typing import Any

from app import regex_patterns as rx
from app.fields import SOURCE_REGEX, SOURCE_SPACY

EMAIL = re.compile(r"\b([A-Za-z0-9._%+-]+)@\s*([A-Za-z0-9.-]+\.[A-Za-z]{2,})\b")
PERSON_NAME = re.compile(
    r"\b((?:M(?:ME|lle)?\.?|Mme|Mr\.?|Monsieur|Madame|Mademoiselle)\s+"
    r"[A-ZÀ-Ÿ][A-Za-zÀ-ÿ'’\-]+"
    r"(?:\s+(?!SIRET\b|SIREN\b|IBAN\b|TVA\b)[A-ZÀ-Ÿ][A-Za-zÀ-ÿ'’\-]+){0,3})",
    re.IGNORECASE,
)

BUSINESS_EMAIL_LOCAL = {
    "contact",
    "compta",
    "comptaclient",
    "comptabilite",
    "comptabilité",
    "info",
    "admin",
    "facturation",
    "commercial",
    "support",
    "assistance",
    "serviceclient",
    "service-client",
    "service_client",
    "noreply",
    "no-reply",
    "no_reply",
    "donotreply",
    "do-not-reply",
    "secretariat",
    "secrétariat",
    "accueil",
    "office",
    "hello",
    "direction",
}

BUSINESS_EMAIL_MARKERS = (
    "serviceclient",
    "service-client",
    "service_client",
    "contact",
    "info",
    "support",
    "assistance",
    "facturation",
    "compta",
    "commercial",
    "accueil",
    "noreply",
    "no-reply",
    "no_reply",
    "donotreply",
)

CONSUMER_EMAIL_DOMAINS = {
    "gmail.com",
    "googlemail.com",
    "yahoo.com",
    "yahoo.fr",
    "hotmail.com",
    "hotmail.fr",
    "outlook.com",
    "outlook.fr",
    "live.com",
    "live.fr",
    "icloud.com",
    "me.com",
    "proton.me",
    "protonmail.com",
    "orange.fr",
    "wanadoo.fr",
    "free.fr",
    "laposte.net",
    "sfr.fr",
    "bbox.fr",
    "aol.com",
}

PERSONAL_EMAIL_LOCAL = re.compile(
    r"^(?:[a-zà-ÿ]{2,}|[a-zà-ÿ])[._-][a-zà-ÿ]{2,}$",
    re.IGNORECASE,
)

PERSON_JUNK = {
    "date",
    "adresse",
    "address",
    "period",
    "période",
    "facture",
    "iban",
    "siret",
    "tva",
    "vos",
    "votre",
    "nom",
}

LEGAL_HINT = re.compile(
    r"\b(SARL|SASU|SAS|EURL|SCI|SELARL|SA\b|SIRET|TVA|RCS|soci[eé]t[eé])\b",
    re.IGNORECASE,
)
PERSON_HINT = re.compile(r"\b(M(?:ME|lle)?\.?|Mme|Mr\.?|Monsieur|Madame|Mademoiselle)\b", re.IGNORECASE)


def detect_information(text: str, entities: dict[str, Any]) -> dict[str, Any]:
    sources = entities.get("_sources") or {}
    business: list[dict[str, Any]] = []
    personal: list[dict[str, Any]] = []

    siret = entities.get("siret")
    siren = entities.get("siren")
    if siret:
        value = siret if not siren else f"{siret} (SIREN {siren})"
        business.append(_item("siret", "SIRET / SIREN", value, SOURCE_REGEX))

    if entities.get("tvaNumber"):
        business.append(
            _item("vat", "Numéro de TVA", entities["tvaNumber"], SOURCE_REGEX)
        )

    org = entities.get("companyName") or entities.get("bankName")
    if org:
        business.append(
            _item(
                "organisation",
                "Organisation",
                org,
                sources.get("companyName") or sources.get("bankName") or SOURCE_REGEX,
            )
        )

    iban = entities.get("iban")
    holder_personal = _holder_is_person(entities)
    iban_kind = _classify_iban(text, entities) if iban else None
    if iban and iban_kind != "personal":
        business.append(_item("iban", "IBAN", iban, SOURCE_REGEX))

    if entities.get("address"):
        addr_item = _item(
            "address",
            "Adresse",
            entities["address"],
            sources.get("address") or SOURCE_REGEX,
        )
        addr_kind = _classify_address(text, str(entities["address"]), entities)
        if addr_kind == "personal":
            addr_item["label"] = "Adresse personnelle"
            personal.append(addr_item)
        elif addr_kind == "business":
            business.append(addr_item)

    company_norm = str(org or "").lower()
    seen_persons: set[str] = set()
    for name, source in _person_names(text, entities):
        if _is_company_name(name, company_norm) or not _plausible_person(name):
            continue
        if _in_street_context(text, name):
            continue
        key = name.lower()
        if key in seen_persons:
            continue
        seen_persons.add(key)
        personal.append(_item("person_name", "Nom de personne", name, source))

    for raw_email in EMAIL.finditer(text):
        email = f"{raw_email.group(1)}@{raw_email.group(2)}".replace(" ", "")
        kind = _classify_email(email, org, entities)
        if kind == "personal":
            personal.append(_item("email", "Adresse e-mail", email, SOURCE_REGEX))
        elif kind == "business":
            business.append(_item("email", "E-mail professionnel", email, SOURCE_REGEX))

    for phone_match, phone in rx.iter_fr_phones(text):
        if _classify_phone(text, phone_match.start(), entities) == "personal":
            personal.append(_item("phone", "Numéro de téléphone", phone, SOURCE_REGEX))
        else:
            business.append(_item("phone", "Téléphone", phone, SOURCE_REGEX))

    if iban and iban_kind == "personal":
        personal.append(_item("iban", "IBAN personnel", iban, SOURCE_REGEX))

    business = _dedupe_items(business)
    personal = _dedupe_items(personal)
    categories = list(dict.fromkeys(item["label"] for item in personal))
    entities_out = [
        {"type": item["key"], "value": item["value"], "source": item["source"]}
        for item in personal
    ]

    return {
        "business": business,
        "personal": personal,
        "contains_potential_personal_data": len(personal) > 0,
        "categories": categories,
        "entities": entities_out,
    }


def detect_pii(text: str, entities: dict[str, Any]) -> dict[str, Any]:
    """Backward-compatible view used by older record fields."""
    info = detect_information(text, entities)
    return {
        "present": info["contains_potential_personal_data"],
        "categories": info["categories"],
        "entities": info["entities"],
    }


def _item(key: str, label: str, value: str, source: str) -> dict[str, Any]:
    return {"key": key, "label": label, "value": value, "source": source}


def _normalize_person_name(name: str) -> str:
    return rx.trim_civil_person_name(name)


def _person_names(text: str, entities: dict[str, Any]) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for match in PERSON_NAME.finditer(text):
        found.append((_normalize_person_name(match.group(1)), SOURCE_REGEX))
    for match in rx.CUSTOMER_LABEL_LINE.finditer(text):
        raw = re.sub(r"\s+", " ", match.group(1)).strip()
        name = _normalize_person_name(raw) if PERSON_HINT.search(raw) else raw
        if name:
            found.append((name, SOURCE_REGEX))
    raw = entities.get("rawEntities") or {}
    for person in raw.get("persons") or []:
        value = str(person).strip()
        name = _normalize_person_name(value) if PERSON_HINT.search(value) else value
        if name:
            found.append((name, SOURCE_SPACY))
    collapsed: list[tuple[str, str]] = []
    for name, source in found:
        if any(name.lower() != other.lower() and name.lower() in other.lower() for other, _ in found):
            continue
        collapsed.append((name, source))
    return collapsed


def _plausible_person(name: str) -> bool:
    compact = name.strip().lower()
    if compact in PERSON_JUNK or len(compact) < 5:
        return False
    tokens = set(re.findall(r"[a-zà-ÿ]+", compact))
    label_tokens = PERSON_JUNK | {
        "contribution",
        "tarifaire",
        "taxe",
        "attestation",
        "vigilance",
        "cle",
        "rib",
        "bic",
        "swift",
        "iban",
        "rue",
        "avenue",
        "document",
        "facture",
    }
    if PERSON_HINT.search(name):
        return True
    if re.search(r"\d", name):
        return False
    tokens_list = [tok for tok in name.split() if tok]
    if tokens_list and all(tok[:1].islower() for tok in tokens_list):
        return False
    if tokens & label_tokens:
        return False
    return len(name.split()) >= 2


def _dedupe_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str]] = set()
    unique: list[dict[str, Any]] = []
    for item in items:
        key = (item["key"], re.sub(r"\s+", "", item["value"]).lower())
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def _in_street_context(text: str, name: str) -> bool:
    if not name or len(name) < 4:
        return False
    return bool(
        re.search(
            rf"\b(?:rue|avenue|av\.|bd|boulevard|chemin|place|all[ée]e|allee|impasse)\s+{re.escape(name)}\b",
            text,
            re.IGNORECASE,
        )
    )


def _is_company_name(name: str, company_norm: str) -> bool:
    if LEGAL_HINT.search(name):
        return True
    lowered = name.lower()
    if company_norm and (lowered in company_norm or company_norm in lowered):
        return True
    return False


def _is_business_local(local_root: str) -> bool:
    compact = re.sub(r"[^a-z0-9]", "", local_root)
    if local_root in BUSINESS_EMAIL_LOCAL or local_root.startswith("compta"):
        return True
    if any(marker in local_root for marker in BUSINESS_EMAIL_MARKERS):
        return True
    if any(re.sub(r"[^a-z0-9]", "", marker) in compact for marker in BUSINESS_EMAIL_MARKERS):
        return True
    parts = re.split(r"[._\-]+", local_root)
    return any(part in BUSINESS_EMAIL_LOCAL for part in parts if part)


def _classify_email(email: str, org: str | None, entities: dict[str, Any]) -> str:
    local, _, domain = email.lower().partition("@")
    local_root = local.split("+")[0]
    if _is_business_local(local_root):
        return "business"
    if PERSONAL_EMAIL_LOCAL.match(local_root):
        return "personal"
    if domain in CONSUMER_EMAIL_DOMAINS:
        return "personal"
    tokens = _org_tokens(org, entities)
    domain_compact = re.sub(r"[^a-z0-9]", "", domain)
    if any(token in domain_compact for token in tokens if len(token) >= 3):
        return "business"
    return "business"


def _org_tokens(org: str | None, entities: dict[str, Any]) -> list[str]:
    blobs = [org or ""]
    raw = entities.get("rawEntities") or {}
    blobs.extend(str(x) for x in (raw.get("orgs") or [])[:3])
    tokens: list[str] = []
    for blob in blobs:
        for word in re.findall(r"[a-zà-ÿ]{4,}", blob.lower()):
            if word not in {"sarl", "sasu", "les", "des", "pour"}:
                tokens.append(re.sub(r"[^a-z0-9]", "", word))
    return tokens


def _holder_is_person(entities: dict[str, Any]) -> bool:
    holder = str(entities.get("accountHolder") or "")
    if PERSON_HINT.search(holder):
        return True
    if entities.get("documentType") == "RIB" and not entities.get("siret"):
        if holder and not LEGAL_HINT.search(holder):
            return True
    return False


def _context_window(text: str, needle: str, radius: int = 280) -> str:
    if not text or not needle:
        return ""
    hay = re.sub(r"\s+", " ", rx.fold_layout(text))
    needle_n = re.sub(r"\s+", " ", rx.fold_layout(needle)).strip()
    idx = hay.lower().find(needle_n.lower()[:60])
    if idx < 0:
        postal = re.search(r"(\d{5}\s+[A-Za-zÀ-ÿ].{0,40})$", needle_n)
        if postal:
            idx = hay.lower().find(postal.group(1).lower())
    if idx < 0:
        return ""
    return hay[max(0, idx - radius) : min(len(hay), idx + max(len(needle_n), 8) + radius)]


_SERVICE_CONTEXT = re.compile(
    r"(?i)service\s+(?:client|consommateurs?|abonn|gratuit)"
)
_PERSONAL_ADDR_CONTEXT = re.compile(
    r"(?i)\btitulaire\b|\babonn[ée]e?s?\b|\bcliente?s?\b|"
    r"adresse\s+du\s+client|adresse\s+de\s+facturation|"
    r"vos\s+coordonn[ée]es|coordonn[ée]es\s+du\s+client|"
    r"n[°ºo]?\s*d['eé]?\s*ligne|num[eé]ro\s+de\s+ligne|"
    r"\bidentifiant\b|n[°ºo]?\s*client"
)
_BUSINESS_ADDR_CONTEXT = re.compile(
    r"(?i)si[eè]ge\s+social|soci[eé]t[eé]|[eé]metteur|"
    r"adresse\s+de\s+l['’]entreprise|capital\s+social|\brcs\b|\bsiret\b"
)


def _classify_address(text: str, address: str, entities: dict[str, Any]) -> str:
    if _holder_is_person(entities):
        return "personal"
    window = _context_window(text, address)
    if not window:
        return "uncertain"
    cleaned = _SERVICE_CONTEXT.sub(" ", window)
    legal = bool(
        re.search(
            r"(?i)\bsiret\b|\brcs\b|si[eè]ge\s+social|capital\s+social|\bau capital\b",
            window,
        )
    )
    subscriber = bool(
        _PERSONAL_ADDR_CONTEXT.search(cleaned) or rx.has_subscriber_field(window)
    )
    if legal and not subscriber:
        return "business"
    business = 0
    personal = 0
    if _BUSINESS_ADDR_CONTEXT.search(window) or legal:
        business += 2
    if _SERVICE_CONTEXT.search(window):
        business += 1
    if subscriber:
        personal += 2
    if PERSON_HINT.search(cleaned) and not legal:
        personal += 2
    for person in (entities.get("rawEntities") or {}).get("persons") or []:
        value = str(person).strip()
        if len(value) >= 5 and value.lower() in window.lower() and subscriber:
            personal += 2
            break
    if personal > business:
        return "personal"
    if business > personal:
        return "business"
    return "uncertain"


def _classify_iban(text: str, entities: dict[str, Any]) -> str:
    if _holder_is_person(entities):
        return "personal"
    if entities.get("documentType") in {"FACTURE", "DEVIS", "KBIS", "SIRET_ATTESTATION"}:
        return "business"
    if entities.get("siret") or LEGAL_HINT.search(str(entities.get("companyName") or "")):
        return "business"
    match = rx.IBAN.search(text)
    if not match:
        return "business"
    start = max(0, match.start() - 180)
    end = min(len(text), match.end() + 180)
    window = text[start:end]
    if LEGAL_HINT.search(window):
        return "business"
    if PERSON_HINT.search(window) and not LEGAL_HINT.search(window):
        return "personal"
    return "business"


def _classify_phone(text: str, index: int, entities: dict[str, Any]) -> str:
    window = text[max(0, index - 120) : min(len(text), index + 80)]
    folded = rx.fold_layout(window)
    if rx.has_subscriber_field(folded) or (
        PERSON_HINT.search(folded) and not _SERVICE_CONTEXT.search(folded)
    ):
        if not _BUSINESS_ADDR_CONTEXT.search(folded):
            return "personal"
    if _SERVICE_CONTEXT.search(folded) or LEGAL_HINT.search(folded):
        return "business"
    if entities.get("siret"):
        return "business"
    return "business"
