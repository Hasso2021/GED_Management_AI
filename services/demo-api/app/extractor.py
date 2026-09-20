"""
Entity extraction combining spaCy NER and regex patterns.
Returns a dict of extracted fields keyed by document type.
"""
from typing import Any, Optional
import re
import unicodedata
import spacy
from app.config import settings
from app.logger import logger
from app import regex_patterns as rx


_nlp: Optional[spacy.language.Language] = None

_NER_JUNK = {
    "period",
    "periode",
    "période",
    "quantité",
    "quantite",
    "prixhoraire",
    "prix",
    "horaire",
    "montant",
    "montnt",
    "facture",
    "datefacture",
    "dateéchéance",
    "dateecheance",
    "description",
    "pescrpten",
    "allocataire",
    "caf",
    "vos",
    "prestation",
    "creche",
    "crèche",
    "règlement",
    "reglement",
    "attestation",
    "vigilance",
    "contribution",
    "tarifaire",
    "realisee",
    "realise",
}

_LABEL_PREFIX = re.compile(
    r"^(?:Émetteur|Emetteur|Fournisseur|Vendor|Raison sociale|Société|Societe|"
    r"Nom|Name|Client|Customer|Adresse|Address)\s*[:\-]\s*",
    re.IGNORECASE,
)
_ISSUER_LABEL = rx.ISSUER_LABEL_LINE

_TOPIC_HEADING_TOKENS = {
    "electricite",
    "gaz",
    "eau",
    "releve",
    "facture",
    "devis",
    "invoice",
    "montant",
    "total",
    "conso",
    "consommation",
    "depannage",
    "urgence",
    "client",
    "identifiant",
    "duplicata",
    "document",
    "prestation",
    "kwh",
    "attestation",
    "vigilance",
}


def _is_topic_heading(value: str) -> bool:
    """True for document topics/service lines, not issuer names."""
    folded = _fold(value)
    if re.search(r"\brelev[eé]\b", folded):
        return True
    if re.search(r"\b(sarl|sasu|sas|eurl|selarl|sci)\b", folded) or re.search(
        r"\bau capital\b", folded
    ):
        return False
    tokens = re.findall(r"[a-zà-ÿ]+", folded)
    content = [tok for tok in tokens if tok not in {"de", "du", "des", "la", "le", "les", "d", "l", "et", "en"}]
    if not content:
        return False
    return all(tok in _TOPIC_HEADING_TOKENS for tok in content)

_LEGAL_FORM_SUFFIX = re.compile(
    r"\b([A-ZÀ-Ÿ][A-Za-zÀ-ÿ0-9&'’ \-]{2,50}?)\s+(SARL|SASU|SAS|EURL|SCI|SELARL)\b",
    re.IGNORECASE,
)

_COMPANY_BEFORE_CAPITAL = re.compile(
    r"\b([A-ZÀ-Ÿ][A-Za-zÀ-ÿ'’ \-]{2,50}?),\s+(?:SA|SAS|SASU|SARL|EURL)\s+au capital",
    re.IGNORECASE,
)

_TITLE_LINE = re.compile(
    r"^(FACTURE|DEVIS|INVOICE|EXTRAIT\s+KBIS|KBIS|RIB|RELEV[EÉ]|ATTESTATION)\b",
    re.IGNORECASE,
)

_DOC_DATE_PATTERNS = (
    re.compile(
        r"Fait\s+à[^\n]{0,60}\n\s*Le\s+(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{4})",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:Fait|Délivr[ée]|Établie|Etablie)\s+(?:le\s*:?\s*)(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{4})",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:Date\s*(?:du document|d['’]émission|d['’]édition|d['’]attestation)?\s*:)\s*"
        r"(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{4})",
        re.IGNORECASE,
    ),
    re.compile(r"(?m)^Le\s+(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{4})\b"),
    re.compile(
        r"(?:Délivr[ée]|Fait)\s+le\s*:?\s*(\d{4}-\d{2}-\d{2})",
        re.IGNORECASE,
    ),
)

_PERSON_RE = re.compile(
    r"\b(M\.|Mme|Mlle|Mr\.?|Monsieur|Madame|Mademoiselle)\s+",
    re.IGNORECASE,
)

_PERSON_NAME_RE = re.compile(
    r"\b((?:M(?:ME|lle)?\.?|Mme|Mr\.?|Monsieur|Madame|Mademoiselle)\s+"
    r"[A-ZÀ-Ÿ][A-Za-zÀ-ÿ'’\-]+"
    r"(?:\s+(?!SIRET\b|SIREN\b|IBAN\b|TVA\b)[A-ZÀ-Ÿ][A-Za-zÀ-ÿ'’\-]+){0,3})",
    re.IGNORECASE,
)

_NAME_PRODUCT_STOP = {
    "forfait",
    "abonnement",
    "abonnements",
    "option",
    "options",
    "facture",
    "total",
    "service",
    "services",
    "communication",
    "communications",
    "internet",
    "identifiant",
    "mobile",
    "sas",
    "sarl",
    "sasu",
    "origine",
    "destination",
    "france",
    "details",
    "détails",
}

_AMOUNT_TTC_KWS = (
    "montant ttc",
    "toutes taxes",
    "ttc :",
    "ttc:",
    "net à payer",
    "net a payer",
    "total ttc",
    "total à payer",
    "total a payer",
    "à payer",
    "a payer",
    "règlement",
    "reglement",
    "prélèvement",
    "prelevement",
)
_AMOUNT_HT_KWS = ("montant ht", "hors taxe", "ht :", "ht:", "total ht")
_AMOUNT_TVA_KWS = ("montant tva", "tva :", "tva:")


def load_nlp() -> spacy.language.Language:
    global _nlp
    if _nlp is None:
        try:
            _nlp = spacy.load(settings.spacy_model)
            logger.info("spacy_model_loaded", model=settings.spacy_model)
        except OSError:
            logger.warning("spacy_model_not_found_using_blank", model=settings.spacy_model)
            _nlp = spacy.blank("fr")
    return _nlp


def _clean_span(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip(" \t\n\r-–|,;:")


def _strip_label_prefix(value: str) -> str:
    return _LABEL_PREFIX.sub("", _clean_span(value)).strip()


def _is_plausible_entity(value: str) -> bool:
    if "\n" in value:
        return False
    text = _clean_span(value)
    if len(text) < 4 or len(text) > 80:
        return False
    if text.upper() in {"IBAN", "BIC", "SIRET", "SIREN", "TVA", "RCS", "CAF", "CESU", "ADRESSE", "ADDRESS"}:
        return False
    tokens = set(re.findall(r"[a-zà-ÿ]+", text.lower()))
    if tokens & _NER_JUNK:
        return False
    if re.fullmatch(r"r[eè]glement\s+\d+", text, re.IGNORECASE):
        return False
    if re.search(r"[!|*]", text):
        return False
    if not re.search(r"[A-Za-zÀ-ÿ]{3,}", text):
        return False
    return True


def _looks_like_person(value: str) -> bool:
    return bool(_PERSON_RE.search(value))


def _looks_like_company_line(line: str) -> bool:
    text = _clean_span(line)
    if not text or len(text) > 80:
        return False
    if _looks_like_person(text) or _is_topic_heading(text):
        return False
    if re.search(r"\d{5}|@|siret|iban|facture|tva|règlement|reglement", text, re.IGNORECASE):
        return False
    if not re.search(r"[A-Za-zÀ-ÿ]{4,}", text):
        return False
    return True


def _fold(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value.lower())
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


def _letterhead_company(text: str) -> Optional[str]:
    for line in text.splitlines():
        line = line.strip()
        if not line or _TITLE_LINE.match(line) or _is_topic_heading(line):
            continue
        if re.fullmatch(r"[A-ZÀ-Ÿ][A-ZÀ-Ÿ0-9'’ \-]{5,60}", line) and len(line.split()) >= 2:
            return _clean_span(line)
        return None
    return None


def _org_context_score(org: str, text: str) -> tuple[int, int, int]:
    folded = _fold(org)
    legal = 2 if re.search(r"\b(sarl|sasu|sas|eurl|sa|sci|selarl)\b", folded) else 0
    idx = text.lower().find(org.lower()[:24]) if org else -1
    window = text[max(0, idx - 100) : idx + len(org) + 100] if idx >= 0 else ""
    ctx = 0
    if re.search(r"capital|siret|rcs|si[eè]ge social", window, re.I):
        ctx += 3
    if 0 <= idx < 2500:
        ctx += 1
    return (legal + ctx, legal, len(org.split()))


def _rank_orgs(ner_orgs: list[str], text: str = "") -> list[str]:
    folded = [_fold(org) for org in ner_orgs]
    kept: list[str] = []
    for i, org in enumerate(ner_orgs):
        if _is_topic_heading(org):
            continue
        if any(
            i != j and folded[i] != folded[j] and folded[i] in folded[j]
            for j, other in enumerate(ner_orgs)
        ):
            continue
        if _is_plausible_entity(org) and not _looks_like_person(org):
            kept.append(org)
    return sorted(kept, key=lambda org: _org_context_score(org, text), reverse=True)


def _brand_from_heading(text: str) -> Optional[str]:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    for i, line in enumerate(lines):
        if re.search(r"\b(FACTURE|DEVIS|INVOICE)\b", line, re.IGNORECASE):
            for nxt in lines[i + 1 : i + 4]:
                if _looks_like_company_line(nxt):
                    return _strip_label_prefix(nxt)
            break
    return None


def _extract_company_name(text: str, ner_orgs: list[str]) -> tuple[Optional[str], Optional[str]]:
    labeled = _ISSUER_LABEL.search(text)
    if labeled:
        candidate = _strip_label_prefix(labeled.group(1))
        if candidate and not _is_topic_heading(candidate) and not _looks_like_person(candidate):
            return candidate, "regex"

    legal = rx.LEGAL_FORM_COMPANY.search(text)
    if legal:
        return _clean_span(legal.group(1)), "regex"

    suffix = _LEGAL_FORM_SUFFIX.search(text)
    if suffix:
        return _strip_label_prefix(suffix.group(0)), "regex"

    capital = rx.COMPANY_AU_CAPITAL.search(text)
    if capital:
        name = capital.group(1).strip(" -,–")
        form = capital.group(2).upper()
        original = capital.group(0)
        joiner = "-" if re.search(rf"{re.escape(name)}\s*-\s*{form}", original, re.I) else " "
        if name and not _is_topic_heading(name):
            return _clean_span(f"{name}{joiner}{form}"), "regex"

    before_capital = _COMPANY_BEFORE_CAPITAL.search(text)
    if before_capital:
        return _clean_span(before_capital.group(1)), "regex"

    letterhead = _letterhead_company(text)
    if letterhead and not _is_topic_heading(letterhead):
        return letterhead, "deterministic_rule"

    brand = _brand_from_heading(text)
    if brand and not _is_topic_heading(brand):
        return brand, "deterministic_rule"

    for org in _rank_orgs(ner_orgs, text):
        cleaned = _strip_label_prefix(org)
        if cleaned and not _is_topic_heading(cleaned):
            return cleaned, "spacy_ner"
    return None, None


def _to_iso_date(raw: str) -> Optional[str]:
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        return raw
    parts = re.split(r"[/\-.]", raw)
    if len(parts) != 3:
        return None
    day, month, year = parts
    if len(year) != 4:
        return None
    return f"{year}-{month.zfill(2)}-{day.zfill(2)}"


def _extract_document_date(text: str) -> tuple[Optional[str], Optional[str]]:
    for pattern in _DOC_DATE_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        iso = _to_iso_date(match.group(1))
        if iso:
            return iso, "regex"
    return None, None


def _extract_address(text: str, ner_locs: list[str]) -> tuple[Optional[str], Optional[str]]:
    postal = rx.POSTAL_ADDRESS.search(text)
    if postal:
        return _clean_span(postal.group(1)), "regex"
    street = rx.STREET_ADDRESS.search(text)
    if street:
        return _clean_span(street.group(1)), "regex"
    for loc in ner_locs:
        if _is_plausible_entity(loc) and re.search(r"\d{5}|rue|avenue", loc, re.IGNORECASE):
            return _clean_span(loc), "spacy_ner"
    return None, None


def _extract_amounts(text: str) -> dict[str, Optional[float]]:
    """Parse HT, TVA, TTC (or paid total) from labelled lines."""
    result: dict[str, Optional[float]] = {"amountHT": None, "amountTVA": None, "amountTTC": None}

    for line in text.split("\n"):
        line_lower = line.lower()
        if "capital" in line_lower:
            continue
        amounts = [rx.normalize_amount(m.group(1)) for m in rx.AMOUNT.finditer(line)]
        amounts = [v for v in amounts if v >= 1]
        if not amounts:
            continue
        val = amounts[-1]

        if any(kw in line_lower for kw in _AMOUNT_HT_KWS):
            result["amountHT"] = val
        elif any(kw in line_lower for kw in _AMOUNT_TVA_KWS) and "intracom" not in line_lower:
            result["amountTVA"] = val
        elif any(kw in line_lower for kw in _AMOUNT_TTC_KWS):
            result["amountTTC"] = val

    if result["amountTTC"] is None:
        labelled = [
            rx.normalize_amount(m.group(1))
            for line in text.split("\n")
            if any(kw in line.lower() for kw in ("total", "montant", "payer"))
            and "capital" not in line.lower()
            for m in rx.AMOUNT.finditer(line)
        ]
        labelled = [v for v in labelled if v >= 1]
        if labelled:
            result["amountTTC"] = max(labelled)

    return result


def extract(text: str, document_type: str) -> dict[str, Any]:
    """Extract structured entities from OCR text based on document type."""
    nlp = load_nlp()
    doc = nlp(text[:100_000])  # cap at 100k chars for performance

    ner_orgs = [
        _clean_span(ent.text)
        for ent in doc.ents
        if ent.label_ == "ORG"
        and _is_plausible_entity(ent.text)
        and not _looks_like_person(ent.text)
    ]
    ner_pers = [
        _clean_span(ent.text)
        for ent in doc.ents
        if ent.label_ == "PER" and _is_plausible_entity(ent.text)
    ]
    ner_locs = [
        _clean_span(ent.text)
        for ent in doc.ents
        if ent.label_ in ("LOC", "GPE") and _is_plausible_entity(ent.text)
    ]
    brand = _brand_from_heading(text)
    if brand and brand not in ner_orgs and not _is_topic_heading(brand):
        ner_orgs = [brand] + ner_orgs
    ner_orgs = list(dict.fromkeys(ner_orgs))
    ner_locs = list(dict.fromkeys(ner_locs))
    regex_persons = [
        rx.trim_civil_person_name(m.group(1))
        for m in _PERSON_NAME_RE.finditer(text)
    ]
    regex_persons.extend(_extract_labelled_customer_names(text))
    regex_persons.extend(_extract_subscriber_block_names(text))
    regex_persons = [name for name in regex_persons if name]
    ner_pers = [
        rx.trim_civil_person_name(name) if _PERSON_RE.search(name) else name
        for name in ner_pers
    ]
    ner_pers = list(dict.fromkeys([*_filter_persons(ner_pers, ner_orgs), *regex_persons]))

    sources: dict[str, str] = {}
    entities: dict[str, Any] = {
        "documentType": document_type,
        "rawEntities": {
            "orgs": ner_orgs[:5],
            "locations": ner_locs[:3],
            "persons": ner_pers[:5],
        },
        "_sources": sources,
    }

    siret_match = rx.SIRET.search(text)
    if siret_match:
        entities["siret"] = rx.normalize_siret(siret_match.group(1))
        entities["siren"] = entities["siret"][:9]
        sources["siret"] = "regex"
        sources["siren"] = "regex"

    tva_match = rx.TVA.search(text)
    if tva_match:
        entities["tvaNumber"] = tva_match.group(0).replace(" ", "").upper()
        sources["tvaNumber"] = "regex"

    company, company_src = _extract_company_name(text, ner_orgs)
    if company and document_type != "RIB":
        entities["companyName"] = company
        sources["companyName"] = company_src or "regex"

    address, address_src = _extract_address(text, ner_locs)
    if address and document_type != "RIB":
        entities["address"] = address
        sources["address"] = address_src or "regex"

    iban_match = rx.IBAN.search(text)
    if iban_match:
        entities["iban"] = rx.normalize_iban(iban_match.group(0))
        sources["iban"] = "regex"

    if document_type in ("FACTURE", "DEVIS"):
        _extract_invoice_fields(text, entities)

    elif document_type == "RIB":
        _extract_rib_fields(text, entities)

    elif document_type == "URSSAF":
        _extract_urssaf_fields(text, entities)
        if not entities.get("companyName"):
            entities["companyName"] = "URSSAF"
            sources["companyName"] = "deterministic_rule"

    elif document_type == "KBIS":
        _extract_kbis_fields(text, entities)

    elif document_type in ("SIRET_ATTESTATION", "UNKNOWN"):
        _extract_generic_fields(text, entities)

    return entities


def _extract_generic_fields(text: str, entities: dict[str, Any]) -> None:
    sources = entities.setdefault("_sources", {})
    doc_date, date_src = _extract_document_date(text)
    if doc_date:
        entities["documentDate"] = doc_date
        sources["documentDate"] = date_src or "regex"

    amounts = _extract_amounts(text)
    entities.update({k: v for k, v in amounts.items() if v is not None})
    if amounts.get("amountTTC") is not None or amounts.get("amountHT") is not None:
        sources["amountTTC" if amounts.get("amountTTC") is not None else "amountHT"] = "regex"
        entities["currency"] = "EUR"


def _filter_persons(names: list[str], orgs: list[str]) -> list[str]:
    org_blob = " ".join(orgs).lower()
    cleaned: list[str] = []
    for name in names:
        if not name or name.lower() in org_blob:
            continue
        if name.upper() in {"ADRESSE", "ADDRESS", "IBAN"}:
            continue
        folded = {tok.lower() for tok in re.findall(r"[a-zà-ÿ]+", name.lower())}
        if folded & rx.NAME_TRAILING_STOP and not _PERSON_RE.search(name):
            continue
        if folded & _NAME_PRODUCT_STOP:
            continue
        if _is_topic_heading(name):
            continue
        cleaned.append(name)
    return cleaned


def _looks_like_customer_name(line: str) -> bool:
    text = _clean_span(line)
    if not text or _is_topic_heading(text):
        return False
    if _looks_like_person(text):
        return True
    tokens = text.split()
    if not (2 <= len(tokens) <= 4):
        return False
    if any(re.search(r"\d", tok) or "@" in tok for tok in tokens):
        return False
    if not all(re.match(r"^[A-ZÀ-Ÿ][A-Za-zÀ-ÿ'’\-]+$", tok) for tok in tokens):
        return False
    folded = {_fold(tok) for tok in tokens}
    if folded & _NAME_PRODUCT_STOP or folded & rx.NAME_TRAILING_STOP:
        return False
    return True


def _extract_labelled_customer_names(text: str) -> list[str]:
    found: list[str] = []
    for match in rx.CUSTOMER_LABEL_LINE.finditer(text):
        raw = _clean_span(match.group(1).split("\n")[0])
        if _PERSON_RE.search(raw):
            name = rx.trim_civil_person_name(raw)
        elif _looks_like_customer_name(raw):
            name = raw
        else:
            continue
        if name:
            found.append(name)
    return found


def _extract_subscriber_block_names(text: str) -> list[str]:
    """Name sitting just above subscriber identifiers (n° de ligne, identifiant, n° client)."""
    found: list[str] = []
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if not rx.has_subscriber_field(line):
            continue
        for prev in reversed(lines[max(0, i - 3) : i]):
            prev = prev.strip()
            if not prev:
                continue
            if rx.has_subscriber_field(prev):
                continue
            if _looks_like_customer_name(prev):
                if _PERSON_RE.search(prev):
                    found.append(rx.trim_civil_person_name(prev))
                else:
                    found.append(_clean_span(prev))
            break
    return found


def _extract_invoice_fields(text: str, entities: dict[str, Any]) -> None:
    sources = entities.setdefault("_sources", {})
    invoice_match = rx.INVOICE_NUMBER.search(text)
    if invoice_match:
        number = invoice_match.group(1).strip()
        compact = re.sub(r"\D", "", number)
        digit_only = not re.search(r"[A-Za-z]", number)
        reliable = (
            re.search(r"\d", number)
            and number.upper() not in {"FACTURE", "DEVIS", "INVOICE"}
            and not (digit_only and len(compact) in {8, 9, 14})
        )
        if reliable:
            entities["invoiceNumber"] = re.sub(r"[^\w\-/]", "", number)
            sources["invoiceNumber"] = "regex"

    dates = rx.DATE.findall(text)
    if dates:
        d, m, y = dates[0]
        entities["invoiceDate"] = f"{y}-{m.zfill(2)}-{d.zfill(2)}"
        sources["invoiceDate"] = "regex"
        if len(dates) > 1:
            d2, m2, y2 = dates[1]
            entities["dueDate"] = f"{y2}-{m2.zfill(2)}-{d2.zfill(2)}"
            sources["dueDate"] = "regex"

    amounts = _extract_amounts(text)
    entities.update({k: v for k, v in amounts.items() if v is not None})
    if amounts.get("amountTTC") is not None or amounts.get("amountHT") is not None:
        sources["amountTTC" if amounts.get("amountTTC") is not None else "amountHT"] = "regex"
    entities["currency"] = "EUR"

    rate_match = re.search(r"TVA\s+(\d{1,2}(?:[,\.]\d+)?)\s*%", text, re.IGNORECASE)
    if rate_match:
        entities["tvaRate"] = float(rate_match.group(1).replace(",", "."))
        sources["tvaRate"] = "regex"


def _extract_rib_fields(text: str, entities: dict[str, Any]) -> None:
    sources = entities.setdefault("_sources", {})

    iban_match = rx.IBAN.search(text)
    if iban_match:
        entities["iban"] = rx.normalize_iban(iban_match.group(0))
        sources["iban"] = "regex"

    holder, bic = _parse_rib_titulaire(text)
    if holder:
        entities["accountHolder"] = holder
        sources["accountHolder"] = "deterministic_rule"
        persons = entities.setdefault("rawEntities", {}).setdefault("persons", [])
        if holder not in persons:
            persons.insert(0, holder)

    if bic:
        entities["bic"] = bic
        sources["bic"] = "regex"

    bank = _parse_rib_bank(text)
    if bank:
        entities["bankName"] = bank
        entities["companyName"] = bank
        sources["bankName"] = "deterministic_rule"
        sources["companyName"] = "deterministic_rule"

    address = _parse_rib_holder_address(text)
    if address:
        entities["address"] = address
        sources["address"] = "regex"


def _fix_ocr_civility(line: str) -> str:
    return re.sub(r"^Mile\b", "Mme", line.strip(), flags=re.IGNORECASE)


def _parse_rib_titulaire(text: str) -> tuple[Optional[str], Optional[str]]:
    match = re.search(
        r"Titulaire(?:\s+du\s+compte)?[^\n]*\n([^\n]+)",
        text,
        re.IGNORECASE,
    )
    if not match:
        return None, None
    line = _fix_ocr_civility(match.group(1))
    parts = line.split()
    tail: list[str] = []
    while parts and re.fullmatch(r"[A-Z]{2,4}|XXX", parts[-1], re.IGNORECASE):
        tail.insert(0, parts.pop().upper())
    compact = "".join(tail)
    bic = compact if len(compact) in (8, 11) else None
    holder = re.sub(r"\s+", " ", " ".join(parts)).strip(" -/")
    holder = re.sub(r"\b(BIC|SWIFT)\b", "", holder, flags=re.IGNORECASE).strip()
    if holder and len(holder) < 4:
        holder = None
    return holder, bic


def _parse_rib_bank(text: str) -> Optional[str]:
    known = [
        "BoursoBank",
        "Boursorama",
        "BNP Paribas",
        "Société Générale",
        "Crédit Agricole",
        "Crédit Mutuel",
        "Caisse d'Épargne",
        "La Banque Postale",
        "LCL",
        "HSBC",
        "CIC",
        "Hello bank",
        "Fortuneo",
        "ING",
    ]
    blob = text.lower()
    for name in known:
        if name.lower() in blob:
            return name
    match = re.search(r"Domiciliation\s*\n\s*([^\n]+)", text, re.IGNORECASE)
    if match:
        line = match.group(1).strip()
        line = re.sub(r"\bRIB\b", "", line, flags=re.IGNORECASE).strip()
        if line and "code banque" not in line.lower() and len(line) <= 60:
            return line[:80]
    return None


def _parse_rib_holder_address(text: str) -> Optional[str]:
    block_match = re.search(
        r"Titulaire(?:\s+du\s+compte)?(.{0,400}?)(?:IBAN|Domiciliation)",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    block = block_match.group(1) if block_match else text
    two_line = re.search(
        rf"(\d{{1,4}}\s+(?:rue|avenue|av\.|bd|boulevard|chemin|place|all[ée]e|allee|impasse)\s+[A-Za-zÀ-ÿ0-9'’\-\s]{{2,40}}?)\s*\n\s*(\d{{5}}\s+(?:(?!IBAN\b|BIC\b)[A-ZÀ-Ÿ][A-Za-zÀ-ÿ'’\-]+(?:\s+(?!IBAN\b|BIC\b)[A-ZÀ-Ÿ][A-Za-zÀ-ÿ'’\-]+){{0,4}}))",
        block,
        re.IGNORECASE,
    )
    if two_line:
        return _clean_span(f"{two_line.group(1)} {two_line.group(2)}")
    street = rx.STREET_ADDRESS.search(block)
    if street:
        return _clean_span(street.group(1))
    return None


def _extract_urssaf_fields(text: str, entities: dict[str, Any]) -> None:
    sources = entities.setdefault("_sources", {})
    period_match = re.search(
        r"[Pp]ériode\s+(?:du\s+)?(\d{1,2}/\d{1,2}/\d{4})(?:\s+au\s+(\d{1,2}/\d{1,2}/\d{4}))?",
        text,
    )
    if period_match:
        entities["urssafPeriod"] = period_match.group(0).strip()
        sources["urssafPeriod"] = "regex"

    trimestre = re.search(
        r"(\d(?:er|e|ème)?\s+trimestre\s+20\d{2})",
        text,
        re.IGNORECASE,
    )
    if trimestre and not entities.get("urssafPeriod"):
        entities["urssafPeriod"] = re.sub(r"\s+", " ", trimestre.group(1)).strip()
        sources["urssafPeriod"] = "regex"

    exp_match = re.search(
        r"(?:valable jusqu(?:['`])?au|expire le|date limite)\s*:?\s*(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{4})",
        text,
        re.IGNORECASE,
    )
    if exp_match:
        raw_date = exp_match.group(1)
        parts = re.split(r"[/\-.]", raw_date)
        if len(parts) == 3:
            entities["urssafExpirationDate"] = f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
            entities.setdefault("_sources", {})["urssafExpirationDate"] = "regex"

    if re.search(r"à jour|réguli[eè]re?|conforme", text, re.IGNORECASE):
        entities["urssafStatus"] = "VALID"
    elif re.search(r"irréguli[eè]re?|défaut|impayé", text, re.IGNORECASE):
        entities["urssafStatus"] = "INVALID"


def _extract_kbis_fields(text: str, entities: dict[str, Any]) -> None:
    rcs_match = re.search(
        r"RCS\s+[A-Za-zÀ-ÿ\s\-]+?\s+(?:[A-Z]\s+)?(\d{3}[\s]?\d{3}[\s]?\d{3})\b",
        text,
    )
    if rcs_match:
        entities["registrationNumber"] = re.sub(r"\s", "", rcs_match.group(1))

    court_match = re.search(
        r"[Gg]reffe\s+(?:du\s+[Tt]ribunal\s+)?(?:de\s+)?([A-Z][a-z\-]+(?:\s+[A-Z][a-z\-]+)*)",
        text,
    )
    if court_match:
        entities["registrationCourt"] = court_match.group(1).strip()

    lf_match = re.search(
        r"\b(SAS|SARL|SA|SNC|EURL|SASU|SCI|SELARL|GIE|Association loi 1901)\b",
        text,
        re.IGNORECASE,
    )
    if lf_match:
        entities["legalForm"] = lf_match.group(1).upper()

    cap_match = re.search(r"[Cc]apital\s+(?:social\s+)?(?:de\s+)?([\d\s.,]+)\s*(?:€|EUR|euros?)", text)
    if cap_match:
        entities["shareCapital"] = rx.normalize_amount(cap_match.group(1))
        sources = entities.setdefault("_sources", {})
        sources["shareCapital"] = "regex"

    dates = rx.DATE.findall(text)
    if dates:
        d, m, y = dates[0]
        entities["incorporationDate"] = f"{y}-{m.zfill(2)}-{d.zfill(2)}"
        entities.setdefault("_sources", {})["incorporationDate"] = "regex"
