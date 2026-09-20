"""
Keyword-based fallback classifier.
Returns the document type with the highest keyword match score.
"""
from __future__ import annotations

import re

KEYWORD_MAP: dict[str, list[str]] = {
    "FACTURE": [
        "facture", "invoice", "numéro de facture", "date de facture", "montant ttc",
        "montant ht", "tva", "règlement", "échéance", "bon de commande",
    ],
    "DEVIS": [
        "devis", "estimation", "proposition commerciale", "offre de prix",
        "validité du devis", "acceptation", "bon pour accord",
    ],
    "KBIS": [
        "extrait kbis", "registre du commerce", "rcs", "greffe", "immatriculation",
        "capital social", "forme juridique", "siège social", "représentant légal",
    ],
    "URSSAF": [
        "urssaf", "ursaaf", "cotisations sociales", "attestation de vigilance",
        "cotisant", "période de référence", "régularité", "contributions sociales",
        "micro-social", "protection sociale", "chiffre d'affaires", "cotisations",
        "régime micro",
    ],
    "RIB": [
        "relevé d'identité bancaire", "iban", "swift",
        "domiciliation bancaire", "numéro de compte", "code banque", "code guichet",
        "code bic", "bic/swift",
    ],
    "SIRET_ATTESTATION": [
        "attestation siret", "avis de situation", "situation au répertoire",
        "répertoire sirene", "insee", "numéro siret",
    ],
}

FILENAME_HINTS: dict[str, list[str]] = {
    "URSSAF": ["urssaf", "ursaaf", "ursaff"],
    "FACTURE": ["facture", "invoice"],
    "DEVIS": ["devis"],
    "KBIS": ["kbis"],
    "RIB": ["rib"],
    "SIRET_ATTESTATION": ["siret"],
}

DISTINCTIVE: dict[str, list[str]] = {
    "FACTURE": ["facture", "invoice"],
    "DEVIS": ["devis"],
    "KBIS": ["kbis", "extrait kbis"],
    "URSSAF": ["urssaf", "ursaaf", "ursaff"],
    "SIRET_ATTESTATION": ["insee", "sirene", "avis de situation", "attestation siret"],
}

RIB_TITLE = ("relevé d'identité bancaire",)
RIB_CORE = ("iban", "bic", "swift", "titulaire", "domiciliation")
RIB_WEAK = ("banque", "compte", "code banque", "code guichet")


def _normalize(text: str) -> str:
    return text.lower().replace("’", "'").replace("`", "'").replace("_", " ").replace("-", " ")


def _keyword_hits(blob: str, keyword: str) -> bool:
    if len(keyword) <= 4:
        return re.search(rf"\b{re.escape(keyword)}\b", blob) is not None
    return keyword in blob


def classify_by_keywords(text: str, filename: str = "") -> tuple[str, float]:
    """
    Returns (document_type, confidence_score).
    """
    text_lower = _normalize(text)
    file_lower = _normalize(filename)

    scores: dict[str, int] = {}
    for doc_type, keywords in KEYWORD_MAP.items():
        score = sum(1 for kw in keywords if _keyword_hits(text_lower, kw))
        for hint in FILENAME_HINTS.get(doc_type, []):
            if re.search(rf"\b{re.escape(hint)}\b", file_lower):
                score += 2
        scores[doc_type] = score

    best_type = max(scores, key=lambda k: scores[k])
    best_score = scores[best_type]

    if best_score == 0:
        return "UNKNOWN", 0.0

    ranked = sorted(scores.values(), reverse=True)
    second = ranked[1] if len(ranked) > 1 else 0
    if second == 0:
        confidence = min(1.0, 0.45 + 0.15 * best_score)
    else:
        confidence = best_score / (best_score + second)

    distinctive_blob = f"{text_lower} {file_lower}"
    if has_distinctive_evidence(text, filename, best_type):
        confidence = max(confidence, 0.75 if best_score >= 2 else 0.6)
    if best_type == "URSSAF" and any(_keyword_hits(distinctive_blob, h) for h in FILENAME_HINTS["URSSAF"]):
        confidence = max(confidence, 0.75)

    return best_type, round(min(confidence, 0.99), 4)


def _rib_contextual_evidence(blob: str) -> bool:
    """IBAN alone is not enough; require a banking context combination."""
    if any(_keyword_hits(blob, token) for token in RIB_TITLE):
        return True
    core_hits = [token for token in RIB_CORE if _keyword_hits(blob, token)]
    weak_hits = sum(1 for token in RIB_WEAK if _keyword_hits(blob, token))
    if not core_hits:
        return False
    if core_hits == ["iban"] and weak_hits == 0:
        return False
    return len(core_hits) >= 2 or (len(core_hits) >= 1 and weak_hits >= 2)


def looks_like_rib_document(text: str, filename: str = "") -> bool:
    """True when the document itself is a RIB, not merely a bill that prints an IBAN."""
    return _rib_contextual_evidence(f"{_normalize(text)} {_normalize(filename)}")


def has_distinctive_evidence(text: str, filename: str, document_type: str) -> bool:
    """True only when the class has a type-specific token, not shared footer legalese."""
    blob = f"{_normalize(text)} {_normalize(filename)}"
    if document_type == "RIB":
        return _rib_contextual_evidence(blob)
    return any(_keyword_hits(blob, token) for token in DISTINCTIVE.get(document_type, []))
