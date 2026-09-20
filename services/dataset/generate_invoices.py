#!/usr/bin/env python3
"""
generate_invoices.py — Generates synthetic French invoice/devis PDF files.

Usage:
  python generate_invoices.py --count 50 --output ./samples/invoices
"""
import argparse
import random
import string
from datetime import date, timedelta
from pathlib import Path


def luhn_complete(n: int, length: int = 14) -> str:
    """Generate a number with a valid Luhn checksum."""
    base = str(n).zfill(length - 1)
    total = 0
    alternate = True
    for ch in reversed(base):
        d = int(ch)
        if alternate:
            d *= 2
            if d > 9:
                d -= 9
        total += d
        alternate = not alternate
    check = (10 - (total % 10)) % 10
    return base + str(check)


def random_siret() -> str:
    """Generate a valid SIRET (14 digits with Luhn checksum)."""
    base = random.randint(100_000_000_000_0, 999_999_999_999_9) // 10
    return luhn_complete(base, 14)


def random_tva(siret: str) -> str:
    """Derive a plausible TVA from SIREN."""
    siren = siret[:9]
    key = (12 + 3 * int(siren)) % 97
    return f"FR{key:02d}{siren}"


def random_company() -> str:
    words = ["ACME", "TECHNO", "SERVICES", "GROUPE", "SOLUTIONS", "CONSULTING", "INNOV", "DIGITAL"]
    return f"{random.choice(words)} {random.choice(words)} {random.choice(['SAS', 'SARL', 'SA', 'SASU'])}"


def random_invoice_number() -> str:
    year = date.today().year
    seq = random.randint(1, 9999)
    return f"FAC-{year}-{seq:04d}"


def random_date_pair() -> tuple[str, str]:
    base = date.today() - timedelta(days=random.randint(0, 365))
    due = base + timedelta(days=random.choice([30, 45, 60]))
    return base.isoformat(), due.isoformat()


def generate_invoice_text(doc_type: str = "FACTURE") -> str:
    siret = random_siret()
    tva = random_tva(siret)
    company = random_company()
    invoice_num = random_invoice_number() if doc_type == "FACTURE" else random_invoice_number().replace("FAC", "DEV")
    inv_date, due_date = random_date_pair()

    amount_ht = round(random.uniform(100, 50000), 2)
    tva_rate = random.choice([5.5, 10.0, 20.0])
    amount_tva = round(amount_ht * tva_rate / 100, 2)
    amount_ttc = round(amount_ht + amount_tva, 2)

    header = "FACTURE" if doc_type == "FACTURE" else "DEVIS"

    return f"""{header}

Émetteur: {company}
SIRET: {siret}
Numéro TVA intracommunautaire: {tva}
Adresse: {random.randint(1, 99)} rue de la Paix, {random.randint(10000, 99999)} Paris

N° {header}: {invoice_num}
Date de {header.lower()}: {inv_date}
{"Date d'échéance: " + due_date if doc_type == "FACTURE" else "Validité du devis: 30 jours"}

Désignation                    Quantité    PU HT       Total HT
-------------------------------------------------------------------
Prestation de service              1     {amount_ht:.2f} €    {amount_ht:.2f} €

Montant HT :       {amount_ht:.2f} €
TVA {tva_rate:.1f}% :       {amount_tva:.2f} €
Montant TTC :      {amount_ttc:.2f} €

{"Règlement par virement bancaire à réception de facture." if doc_type == "FACTURE" else "Bon pour accord : ____________________"}
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic French invoice/devis text files")
    parser.add_argument("--count", type=int, default=50, help="Number of documents to generate")
    parser.add_argument("--output", type=str, default="./samples/invoices")
    parser.add_argument("--type", choices=["FACTURE", "DEVIS", "MIXED"], default="MIXED")
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    for i in range(args.count):
        if args.type == "MIXED":
            doc_type = random.choice(["FACTURE", "DEVIS"])
        else:
            doc_type = args.type

        text = generate_invoice_text(doc_type)
        prefix = "facture" if doc_type == "FACTURE" else "devis"
        out_path = output_dir / f"{prefix}_{i+1:04d}.txt"
        out_path.write_text(text, encoding="utf-8")

    print(f"Generated {args.count} {args.type} documents in {output_dir}")


if __name__ == "__main__":
    main()
