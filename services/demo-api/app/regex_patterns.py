"""
Compiled regex patterns for French administrative document entity extraction.
"""
import re
import unicodedata

# SIRET: 14 digits, optionally space-separated in groups of 3/5
SIRET = re.compile(r"\b(\d{3}[\s.]?\d{3}[\s.]?\d{3}[\s.]?\d{5})\b")

# SIREN: 9 digits
SIREN = re.compile(r"\b(\d{3}[\s.]?\d{3}[\s.]?\d{3})\b")

# TVA intracommunautaire: FR + 2 alphanum + 9 digits
TVA = re.compile(r"\bFR\s*([A-Z0-9]{2})\s*(\d{3})\s*(\d{3})\s*(\d{3})\b", re.IGNORECASE)

# French IBAN: FR + 2 digits + 23 alphanumeric (spaces allowed)
IBAN = re.compile(r"\bFR\s*\d{2}(?:\s*[A-Z0-9]{4}){5}\s*[A-Z0-9]{3}\b", re.IGNORECASE)

# BIC/SWIFT: 8 or 11 chars (4 letters + 2 letters + 2 alphanums + optional 3)
BIC = re.compile(r"\b([A-Z]{4}[A-Z]{2}[A-Z0-9]{2}(?:[A-Z0-9]{3})?)\b")

# Euro amounts: 1 700,00 / 1.700,00 / 8036.28 / 700,00 — grouped thousands first
AMOUNT = re.compile(
    r"(?:€\s*)?("
    r"\d{1,3}(?:[\s.]\d{3})+[,\.]\d{2}"
    r"|"
    r"\d+[,\.]\d{2}"
    r")\s*(?:€|EUR)?"
)

# Invoice / quote number, tolerant of OCR ("Facturen'", "N° FACTURE:")
INVOICE_NUMBER = re.compile(
    r"(?:(?:n[°ºo'\"]?|num[ée]ro|r[ée]f\.?)\s*(?:de\s+)?(?:facture|devis)"
    r"|facture\s*n[°ºo'\"]?"
    r"|devis\s*n[°ºo'\"]?)"
    r"\s*:?\s*"
    r"([A-Z]{1,5}[-/]\d{2,6}[-/][A-Z0-9]{2,12}"
    r"|[A-Z]{2,6}\d{3,12}"
    r"|[A-Z0-9][A-Z0-9\-/]{3,19})",
    re.IGNORECASE,
)

# Date patterns: DD/MM/YYYY or DD-MM-YYYY or DD.MM.YYYY
DATE = re.compile(r"\b(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})\b")

# ISO date: YYYY-MM-DD
ISO_DATE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")

LEGAL_FORM_COMPANY = re.compile(
    r"\b((?:SARL|SASU|SAS|EURL|SNC|SCI|SELARL|SA)\s+[A-Z][A-Z0-9&'’ \-]{1,50}?)"
    r"(?=\s+au capital|\s+-\s+|\s+SIRET|\s*$)",
    re.IGNORECASE,
)

# "ACME-SA au capital" / "ACME SA au capital" — issuer, not a heading.
# Name group stops before the legal form so "EDF-SA" is not swallowed whole.
COMPANY_AU_CAPITAL = re.compile(
    r"\b([A-ZÀ-Ÿ](?:[A-Za-zÀ-ÿ0-9&.]|-(?!(?:SA|SAS|SASU|SARL|EURL)\b)){0,32})"
    r"\s*[-–,]?\s*(SA|SAS|SASU|SARL|EURL)\s+au capital",
    re.IGNORECASE,
)

ISSUER_LABEL_LINE = re.compile(
    r"(?im)^(?:Émetteur|Emetteur|Fournisseur|Raison sociale|Société|Societe|"
    r"Prestataire|Expéditeur|Expediteur)\s*:?\s*(.+)$"
)

NAME_TRAILING_STOP = frozenset(
    {
        "votre",
        "vos",
        "notre",
        "nos",
        "mon",
        "ma",
        "mes",
        "son",
        "sa",
        "ses",
        "le",
        "la",
        "les",
        "un",
        "une",
        "des",
        "du",
        "de",
        "et",
        "ou",
        "pour",
        "avec",
        "sur",
        "par",
        "dans",
        "jusqu",
        "jusque",
        "adresse",
        "email",
        "mail",
        "telephone",
        "tel",
        "tél",
        "client",
        "facture",
        "montant",
        "total",
        "siret",
        "iban",
        "tva",
        "puissance",
        "conso",
        "releve",
        "relève",
        "prochaine",
        "document",
        "duplicata",
        "identifiant",
        "internet",
        "espace",
        "compte",
        "n",
        "no",
        "numero",
        "numéro",
        "mme",
        "mlle",
        "mr",
        "monsieur",
        "madame",
        "mademoiselle",
        "bic",
        "swift",
        "rib",
        "cle",
        "clee",
        "xxx",
        "contribution",
        "tarifaire",
        "taxe",
        "attestation",
        "vigilance",
    }
)


def trim_civil_person_name(raw: str) -> str:
    """Keep civility + name tokens; stop at labels and ordinary sentence words."""
    cleaned = re.sub(r"\s+", " ", raw or "").strip(" \t-–,;")
    cleaned = re.sub(
        r"\s+(SIRET|SIREN|IBAN|BIC|TVA|RCS|N°|Nº|TEL|TÉL)\b.*$",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    parts = cleaned.split()
    if not parts:
        return ""
    kept = [parts[0]]
    name_tokens = 0
    for token in parts[1:]:
        folded = re.sub(r"[^a-zà-ÿ]", "", token.lower())
        if folded in NAME_TRAILING_STOP:
            break
        if re.search(r"[@/]|^\d", token):
            break
        if re.fullmatch(r"(BIC|SWIFT|IBAN|RIB|XXX)", token, re.IGNORECASE):
            break
        if name_tokens >= 2 and re.fullmatch(r"[A-Z]{3,4}", token):
            break
        if not re.match(r"^[A-ZÀ-Ÿ][A-Za-zÀ-ÿ'’\-]*$", token):
            break
        kept.append(token)
        name_tokens += 1
        if len(kept) >= 5:
            break
    return " ".join(kept).strip(" -–,")

_STREET_TYPE = (
    r"(?:rue|avenue|av\.|bd|boulevard|chemin|place|all[ée]e|allee|allées|impasse|cours)"
)
_CITY = (
    r"(?:(?!IBAN\b|BIC\b|SWIFT\b|FR\d)[A-ZÀ-Ÿ][A-Za-zÀ-ÿ'’\-]+"
    r"(?:\s+(?!IBAN\b|BIC\b|SWIFT\b|FR\d)[A-ZÀ-Ÿ][A-Za-zÀ-ÿ'’\-]+){0,4})"
)
_STREET = (
    rf"\d{{1,4}}\s+{_STREET_TYPE}\s+"
    r"[A-Za-zÀ-ÿ0-9'’\-\s]{2,40}?"
)

POSTAL_ADDRESS = re.compile(
    rf"(?:Adresse(?:\s+postale)?\s*:?\s*)({_STREET}\s+\d{{5}}\s+{_CITY})",
    re.IGNORECASE,
)

STREET_ADDRESS = re.compile(
    rf"\b({_STREET}\s+\d{{5}}\s+{_CITY})",
    re.IGNORECASE,
)

# Labelled subscriber/customer lines. Colon required so "Service client" does not match.
CUSTOMER_LABEL_LINE = re.compile(
    r"(?im)^(?:Titulaire(?:\s+du\s+(?:contrat|compte|ligne))?|"
    r"Abonn[ée]e?|Client[e]?|Nom(?:\s+et\s+pr[eé]nom)?|Pr[eé]nom|"
    r"Coordonn[ée]es(?:\s+du\s+client)?|Vos\s+coordonn[ée]es)\s*[:\-–]\s*(.+)$"
)

SUBSCRIBER_FIELD = re.compile(
    r"(?i)n\W{0,4}d['eé]?\s*ligne|num[eé]ro\s+de\s+ligne|"
    r"identifiant|\bligne\s*:|n\W{0,3}client"
)

# French numbers: +33 / 0X then four 2-digit groups. Separators: space, dot, hyphen.
PHONE_FR = re.compile(
    r"(?:(?<!\d)\+33[\s.-]*[1-9](?:[\s.-]*\d{2}){4}|"
    r"(?<![A-Za-z0-9])0[1-9](?:[\s.-]*\d{2}){4})(?!\d)"
)
PHONE_DATE_CHUNK = re.compile(
    r"\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}|\d{4}[-/.]\d{1,2}[-/.]\d{1,2}"
)


def fold_layout(text: str) -> str:
    """NFKC so PDF ligatures/symbols still match subscriber labels."""
    return unicodedata.normalize("NFKC", text or "")


def has_subscriber_field(text: str) -> bool:
    return bool(SUBSCRIBER_FIELD.search(fold_layout(text)))


def is_valid_fr_phone(raw: str) -> bool:
    """True for a realistic FR number; false for date/time table fragments."""
    text = (raw or "").strip()
    if not text or PHONE_DATE_CHUNK.search(text):
        return False
    if re.search(r"\d{4}", text) and re.search(r"[-/.]", text):
        return False
    digits = re.sub(r"\D", "", text)
    if digits.startswith("0033"):
        digits = "0" + digits[4:]
    elif digits.startswith("33") and len(digits) == 11:
        digits = "0" + digits[2:]
    return bool(re.fullmatch(r"0[1-9]\d{8}", digits))


def iter_fr_phones(text: str):
    """Yield (match, normalized display) for valid French telephone numbers."""
    for match in PHONE_FR.finditer(text or ""):
        raw = match.group(0)
        if not is_valid_fr_phone(raw):
            continue
        yield match, re.sub(r"\s+", " ", raw).strip()


def normalize_siret(raw: str) -> str:
    return re.sub(r"[\s.]", "", raw)


def normalize_iban(raw: str) -> str:
    return re.sub(r"\s", "", raw).upper()


def normalize_amount(raw: str) -> float:
    cleaned = re.sub(r"[\s]", "", raw)
    if "," in cleaned and "." in cleaned:
        # 1.700,00 → 1700.00
        cleaned = cleaned.replace(".", "").replace(",", ".")
    else:
        cleaned = cleaned.replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return 0.0
