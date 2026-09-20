#!/usr/bin/env python3
"""
generate_siret.py — Generate synthetic SIRET attestation and KBIS text files.

Usage:
  python generate_siret.py --count 20 --output ./samples/siret
"""
import argparse
import random
from datetime import date, timedelta
from pathlib import Path


def luhn_complete(base_str: str) -> str:
    total = 0
    alternate = True
    for ch in reversed(base_str):
        d = int(ch)
        if alternate:
            d *= 2
            if d > 9:
                d -= 9
        total += d
        alternate = not alternate
    check = (10 - (total % 10)) % 10
    return base_str + str(check)


def random_siret() -> str:
    base = str(random.randint(10_000_000_000_00, 99_999_999_999_99))
    return luhn_complete(base[:13])


def random_company() -> str:
    names = ["DUPONT", "MARTIN", "BERNARD", "THOMAS", "ROBERT", "PETIT", "RICHARD"]
    forms = ["SAS", "SARL", "SA", "SASU", "EURL"]
    return f"{random.choice(names)} & ASSOCIES {random.choice(forms)}"


COURTS = [
    "Paris", "Lyon", "Marseille", "Toulouse", "Bordeaux",
    "Nantes", "Strasbourg", "Lille", "Rennes", "Nice",
]


def generate_siret_attestation() -> str:
    siret = random_siret()
    siren = siret[:9]
    company = random_company()
    issued = date.today() - timedelta(days=random.randint(0, 30))

    return f"""ATTESTATION DE SITUATION AU RÉPERTOIRE SIRENE

Délivrée par l'INSEE

Dénomination : {company}
Numéro SIREN : {siren}
Numéro SIRET (établissement principal) : {siret}

Adresse du siège social :
{random.randint(1, 200)} avenue {random.choice(['de la République', 'du Général de Gaulle', 'Foch', 'de la Liberté'])}
{random.randint(10000, 99999)} {random.choice(COURTS)}

Date de création : {(date.today() - timedelta(days=random.randint(365, 10*365))).isoformat()}
Activité principale (NAF/APE) : {random.randint(6000, 7499)}Z

Situation au {issued.isoformat()} : ACTIF

Cette attestation est délivrée à la demande de l'intéressé.
"""


def generate_kbis() -> str:
    siret = random_siret()
    siren = siret[:9]
    company = random_company()
    court = random.choice(COURTS)
    capital = random.choice([1000, 5000, 10000, 50000, 100000, 500000])
    inc_date = date.today() - timedelta(days=random.randint(365, 20 * 365))
    legal_form = random.choice(["SAS", "SARL", "SA", "SASU"])

    return f"""EXTRAIT KBIS

Greffe du Tribunal de Commerce de {court}
Délivré le : {date.today().isoformat()}

IDENTIFICATION DE L'ENTREPRISE
===================================
Dénomination : {company}
Forme juridique : {legal_form}
Capital social : {capital:,} €
Date d'immatriculation : {inc_date.isoformat()}

NUMÉROS D'IDENTIFICATION
===================================
RCS {court} {siren[0:3]} {siren[3:6]} {siren[6:]}
SIRET (siège) : {siret[:3]} {siret[3:6]} {siret[6:9]} {siret[9:]}

SIÈGE SOCIAL
===================================
{random.randint(1, 200)} rue {random.choice(['de la Paix', 'du Commerce', 'des Entrepreneurs', 'Victor Hugo'])}
{random.randint(10000, 99999)} {court}

REPRÉSENTANT LÉGAL
===================================
Président : {random.choice(['Jean', 'Marie', 'Pierre', 'Sophie', 'Lucas'])} {random.choice(['DUPONT', 'MARTIN', 'BERNARD', 'LEFEBVRE'])}

Certifié conforme par le greffier.
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate SIRET attestations and KBIS documents")
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--output", type=str, default="./samples/siret")
    parser.add_argument("--type", choices=["SIRET_ATTESTATION", "KBIS", "MIXED"], default="MIXED")
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    for i in range(args.count):
        doc_type = args.type
        if doc_type == "MIXED":
            doc_type = random.choice(["SIRET_ATTESTATION", "KBIS"])

        if doc_type == "SIRET_ATTESTATION":
            text = generate_siret_attestation()
            name = f"siret_{i+1:04d}.txt"
        else:
            text = generate_kbis()
            name = f"kbis_{i+1:04d}.txt"

        (output_dir / name).write_text(text, encoding="utf-8")

    print(f"Generated {args.count} {args.type} documents in {output_dir}")


if __name__ == "__main__":
    main()
