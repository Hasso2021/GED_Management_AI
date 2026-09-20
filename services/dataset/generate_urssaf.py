#!/usr/bin/env python3
"""Generate varied synthetic French URSSAF / micro-social texts."""
from __future__ import annotations

import argparse
import random
from datetime import date, timedelta
from pathlib import Path

FIRST = [
    "Camille", "Léa", "Hugo", "Inès", "Noah", "Chloé", "Louis", "Manon",
    "Arthur", "Jade", "Adam", "Emma", "Raphaël", "Louise", "Gabriel",
]
LAST = [
    "Moreau", "Lefevre", "Garcia", "Roux", "Fournier", "Girard", "Andre",
    "Mercier", "Dupont", "Lemoine", "Blanc", "Guerin", "Faure", "Chevalier",
]
CITIES = [
    "Lyon", "Nantes", "Toulouse", "Lille", "Rennes", "Bordeaux",
    "Strasbourg", "Montpellier", "Dijon", "Angers",
]
ACTIVITIES = [
    "prestations de services informatiques",
    "conseil en communication",
    "activité de formation",
    "vente de marchandises en ligne",
    "prestations artisanales",
]
REGIMES = ["micro-social", "micro-entrepreneur", "régime micro"]
NATURES = ["BIC", "BNC"]
CENTERS = [
    "URSSAF Rhône-Alpes",
    "URSSAF Île-de-France",
    "URSSAF Pays de la Loire",
    "URSSAF Occitanie",
    "URSSAF Hauts-de-France",
]


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
    return base_str + str((10 - (total % 10)) % 10)


def random_siret() -> str:
    return luhn_complete(str(random.randint(10_000_000_000_00, 99_999_999_999_99))[:13])


def fmt_date(value: date) -> str:
    return value.strftime("%d/%m/%Y")


def fmt_euro(value: float) -> str:
    return f"{value:,.2f}".replace(",", " ").replace(".", ",") + " €"


def person() -> tuple[str, str]:
    return random.choice(FIRST), random.choice(LAST)


def period() -> tuple[str, date, date]:
    year = random.randint(2024, 2026)
    quarter = random.randint(1, 4)
    start_month = 1 + (quarter - 1) * 3
    start = date(year, start_month, 1)
    end_month = start_month + 2
    if end_month == 12:
        end = date(year, 12, 31)
    else:
        end = date(year, end_month + 1, 1) - timedelta(days=1)
    label = f"{quarter}e trimestre {year}"
    if random.random() < 0.35:
        return f"du {fmt_date(start)} au {fmt_date(end)}", start, end
    return label, start, end


def vigilance(idx: int) -> str:
    first, last = person()
    siret = random_siret()
    city = random.choice(CITIES)
    issued = date(2025, 1, 1) + timedelta(days=random.randint(0, 500))
    expiry = issued + timedelta(days=random.choice([90, 180, 365]))
    period_label, _, _ = period()
    center = random.choice(CENTERS)
    blocks = [
        "ATTESTATION DE VIGILANCE",
        f"{center}",
        "Article L8222-1 du Code du travail — articles D243-15 et suivants du Code de la sécurité sociale.",
        f"L'URSSAF atteste que {first} {last}, micro-entrepreneur, SIRET {siret},",
        f"est à jour de ses déclarations et cotisations sociales pour la période {period_label}.",
        f"Régime : {random.choice(REGIMES)} — nature de l'activité : {random.choice(NATURES)}.",
        f"Adresse du cotisant : {random.randint(3, 88)} rue des Ateliers, {random.randint(10000, 88999)} {city}.",
        f"Délivrée le {fmt_date(issued)}. Valable jusqu'au {fmt_date(expiry)}.",
        "Document établi pour justifier de la régularité sociale auprès d'un donneur d'ordre.",
    ]
    if idx % 2:
        blocks[0], blocks[1] = blocks[1], blocks[0]
    return "\n\n".join(blocks) + "\n"


def declaration(idx: int) -> str:
    first, last = person()
    siret = random_siret()
    period_label, start, end = period()
    ca = round(random.uniform(1200, 28500), 2)
    rate = random.choice([0.128, 0.220, 0.061])
    cotis = round(ca * rate, 2)
    due = end + timedelta(days=random.choice([20, 30, 45]))
    nature = random.choice(NATURES)
    activity = random.choice(ACTIVITIES)
    lines = [
        "URSSAF — Déclaration de chiffre d'affaires",
        f"Micro-entrepreneur : {first} {last}",
        f"SIRET : {siret}",
        f"Activité : {activity} ({nature})",
        f"Période de référence : {period_label}",
        f"Chiffre d'affaires déclaré : {fmt_euro(ca)}",
        f"Cotisations sociales estimées : {fmt_euro(cotis)} (taux {rate * 100:.1f} %)",
        f"Échéance de paiement : {fmt_date(due)}",
        "Cette déclaration alimente le régime micro-social.",
        "Référence : Code de la sécurité sociale, articles L613-7 et L133-6-8.",
    ]
    if idx % 3 == 0:
        lines = [lines[0], lines[4], lines[1], lines[2], lines[3], *lines[5:]]
    elif idx % 3 == 1:
        lines = [lines[0], *lines[5:8], *lines[1:5], *lines[8:]]
    return "\n".join(lines) + "\n"


def echeancier(idx: int) -> str:
    first, last = person()
    siret = random_siret()
    center = random.choice(CENTERS)
    year = random.randint(2025, 2026)
    rows = []
    total = 0.0
    for month in random.sample(range(1, 13), k=random.choice([3, 4, 6])):
        amount = round(random.uniform(80, 420), 2)
        total += amount
        due = date(year, month, random.choice([5, 15, 20]))
        rows.append(f"- {due.strftime('%B %Y').capitalize()} : {fmt_euro(amount)} — échéance {fmt_date(due)}")
    header = [
        f"Échéancier des cotisations URSSAF — {year}",
        f"Cotisant : {first} {last}  |  SIRET {siret}",
        f"Centre de rattachement : {center}",
        f"Régime {random.choice(REGIMES)} — {random.choice(NATURES)}",
    ]
    footer = [
        f"Total des cotisations : {fmt_euro(total)}",
        "Paiement par prélèvement après déclaration du chiffre d'affaires.",
        "En cas de retard, majorations prévues à l'article R243-18 du CSS.",
    ]
    if idx % 2:
        return "\n".join([*footer[:1], *header, *rows, *footer[1:]]) + "\n"
    return "\n".join([*header, *rows, *footer]) + "\n"


def situation() -> str:
    first, last = person()
    siret = random_siret()
    period_label, _, _ = period()
    issued = date(2025, 6, 1) + timedelta(days=random.randint(0, 200))
    status = random.choice(
        [
            "à jour de ses cotisations et déclarations",
            "régulière au regard des contributions sociales",
            "conforme pour la période de référence",
        ]
    )
    return f"""Avis de situation — URSSAF

Compte cotisant n° {random.randint(10000000, 99999999)}
Identité : {first} {last}
SIRET : {siret}
Période contrôlée : {period_label}

L'URSSAF certifie que le micro-entrepreneur est {status}.
Protection sociale : affiliation au régime micro-social.
Nature des revenus : {random.choice(NATURES)}.

Édité le {fmt_date(issued)}
Document utilisable comme justificatif de régularité sociale.
"""


def rappel() -> str:
    first, last = person()
    siret = random_siret()
    ca = round(random.uniform(800, 9400), 2)
    cotis = round(ca * 0.220, 2)
    due = date(2026, random.randint(1, 9), random.choice([5, 12, 20]))
    return f"""URSSAF — Relance de déclaration

Madame, Monsieur {last},

Votre déclaration de chiffre d'affaires de micro-entrepreneur (SIRET {siret})
n'est pas encore enregistrée pour la période {due.strftime('%B %Y')}.

Chiffre d'affaires prévisionnel indiqué lors de l'inscription : {fmt_euro(ca)}
Cotisations provisionnelles : {fmt_euro(cotis)}
Échéance : {fmt_date(due)}

Merci de déposer la déclaration sur autoentrepreneur.urssaf.fr
afin d'éviter une taxation d'office des cotisations.

Référence URSSAF : {random.choice(CENTERS)} / {random.randint(100000, 999999)}
"""


TEMPLATES = (vigilance, declaration, echeancier, situation, rappel)


def generate_one(index: int) -> str:
    template = TEMPLATES[index % len(TEMPLATES)]
    if template in (vigilance, declaration, echeancier):
        return template(index)
    return template()


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic URSSAF texts")
    parser.add_argument("--count", type=int, default=35)
    parser.add_argument("--output", type=str, default="./samples/urssaf")
    parser.add_argument("--seed", type=int, default=20260908)
    args = parser.parse_args()

    random.seed(args.seed)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    for i in range(args.count):
        path = output_dir / f"urssaf_{i + 1:04d}.txt"
        path.write_text(generate_one(i), encoding="utf-8")
    print(f"Generated {args.count} URSSAF documents in {output_dir}")


if __name__ == "__main__":
    main()
