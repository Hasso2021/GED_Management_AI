from __future__ import annotations

import csv
from pathlib import Path

from .models import Company


OUTPUT_HEADERS = [
    "company_name",
    "siret",
    "vat_number",
    "address_line_1",
    "address_line_2",
    "postal_code",
    "city",
    "country",
    "naf_code",
]


MISSING_MARKERS = {"", "[ND]", "ND", "N/D", "NON DIFFUSIBLE"}


def _pick(row: dict[str, str], *keys: str) -> str:
    for key in keys:
        value = _sanitize_value(row.get(key, ""))
        if value:
            return value.strip()
    return ""


def _normalize_spaces(value: str) -> str:
    return " ".join(value.split())


def _sanitize_value(value: str) -> str:
    cleaned = _normalize_spaces(str(value).strip())
    if cleaned.upper() in MISSING_MARKERS:
        return ""
    return cleaned


def compute_french_vat_from_siren(siren: str) -> str:
    digits = "".join(ch for ch in siren if ch.isdigit())[:9]
    if len(digits) != 9:
        return ""
    key = (12 + 3 * (int(digits) % 97)) % 97
    return f"FR{key:02d}{digits}"


def build_company_name(row: dict[str, str]) -> str:
    direct_name = _pick(
        row,
        "denominationUsuelleEtablissement",
        "denominationUniteLegale",
        "enseigne1Etablissement",
        "nomUsageUniteLegale",
        "company_name",
    )
    if direct_name:
        return _normalize_spaces(direct_name)

    parts = [
        _pick(row, "prenomUsuelUniteLegale"),
        _pick(row, "nomUniteLegale"),
    ]
    return _normalize_spaces(" ".join(part for part in parts if part))


def normalize_sirene_csv(input_path: Path, output_path: Path, limit: int) -> int:
    input_path = input_path.resolve()
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    count = 0
    seen_sirets: set[str] = set()

    with input_path.open("r", encoding="utf-8-sig", newline="") as source, output_path.open(
        "w", encoding="utf-8", newline=""
    ) as target:
        reader = csv.DictReader(source)
        writer = csv.DictWriter(target, fieldnames=OUTPUT_HEADERS)
        writer.writeheader()

        for row in reader:
            if limit and count >= limit:
                break

            state = _pick(row, "etatAdministratifEtablissement", "etatAdministratifUniteLegale", "etat")
            if state and state.upper() != "A":
                continue

            siret = "".join(ch for ch in _pick(row, "siret", "siretEtablissement") if ch.isdigit())
            if len(siret) != 14 or siret in seen_sirets:
                continue

            company_name = build_company_name(row)
            if not company_name:
                continue

            street_number = _pick(row, "numeroVoieEtablissement", "numeroVoie")
            street_type = _pick(row, "typeVoieEtablissement", "typeVoie")
            street_name = _pick(row, "libelleVoieEtablissement", "libelleVoie")
            address_line_1 = _normalize_spaces(" ".join(part for part in [street_number, street_type, street_name] if part))
            address_line_2 = _pick(row, "complementAdresseEtablissement", "complementAdresse")
            postal_code = _pick(row, "codePostalEtablissement", "codePostal")
            city = _pick(row, "libelleCommuneEtablissement", "libelleCommune")
            country = _pick(row, "libellePaysEtrangerEtablissement")
            naf_code = _pick(row, "activitePrincipaleEtablissement", "activitePrincipaleUniteLegale")
            if not postal_code or not city or not address_line_1:
                continue
            siren = siret[:9]
            vat_number = compute_french_vat_from_siren(siren)

            writer.writerow(
                {
                    "company_name": company_name,
                    "siret": siret,
                    "vat_number": vat_number,
                    "address_line_1": address_line_1,
                    "address_line_2": address_line_2,
                    "postal_code": postal_code,
                    "city": city,
                    "country": country or "France",
                    "naf_code": naf_code,
                }
            )
            seen_sirets.add(siret)
            count += 1

    return count


def load_company_pool(path: Path) -> list[Company]:
    path = path.resolve()
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        companies = [
            Company(
                company_name=_sanitize_value(row["company_name"]),
                siret=row["siret"].strip(),
                vat_number=_sanitize_value(row.get("vat_number", "")),
                address_line_1=_sanitize_value(row.get("address_line_1", "")),
                address_line_2=_sanitize_value(row.get("address_line_2", "")),
                postal_code=_sanitize_value(row.get("postal_code", "")),
                city=_sanitize_value(row.get("city", "")),
                country=_sanitize_value(row.get("country", "")) or "France",
                naf_code=_sanitize_value(row.get("naf_code", "")),
            )
            for row in reader
            if _sanitize_value(row.get("company_name", "")) and row.get("siret") and _sanitize_value(row.get("address_line_1", "")) and _sanitize_value(row.get("postal_code", "")) and _sanitize_value(row.get("city", ""))
        ]
    if len(companies) < 2:
        raise ValueError(f"Le pool d'entreprises doit contenir au moins 2 lignes valides: {path}")
    return companies
