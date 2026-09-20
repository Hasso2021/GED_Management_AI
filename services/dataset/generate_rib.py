#!/usr/bin/env python3
"""Generate varied synthetic French RIB texts (no invoice wording)."""
from __future__ import annotations

import argparse
import random
import string
from pathlib import Path

BANKS = [
    ("Crédit Agricole", "AGRIFRPP"),
    ("BNP Paribas", "BNPAFRPP"),
    ("Société Générale", "SOGEFRPP"),
    ("La Banque Postale", "PSSTFRPP"),
    ("Crédit Mutuel", "CMCIFR2A"),
    ("Caisse d'Épargne", "CEPAFRPP"),
    ("LCL", "CRLYFRPP"),
    ("BoursoBank", "BOUSFRPP"),
    ("CIC", "CMCIFRPA"),
    ("Hello bank", "BNPAFRPP"),
]
FIRST = [
    "Nina", "Sacha", "Mila", "Théo", "Lina", "Eliott", "Zoé", "Aaron",
    "Alice", "Isaac", "Eva", "Paul", "Sarah", "Yanis", "Clara",
]
LAST = [
    "Marchand", "Perrin", "Renard", "Barbier", "Colin", "Picard",
    "Meyer", "Robin", "Gautier", "Lopez", "Masson", "Sanchez",
]
CITIES = [
    "Paris", "Lyon", "Marseille", "Nice", "Tours", "Orléans",
    "Reims", "Grenoble", "Clermont-Ferrand", "Avignon",
]
BRANCHES = [
    "Agence Centre", "Agence République", "Agence Gare",
    "Agence Hôtel de Ville", "Agence Universités",
]


def random_iban() -> str:
    bank = f"{random.randint(10000, 99999):05d}"
    desk = f"{random.randint(10000, 99999):05d}"
    account = "".join(random.choices(string.digits, k=11))
    key = f"{random.randint(10, 97):02d}"
    body = f"FR76{bank}{desk}{account}{key}"
    return " ".join(body[i : i + 4] for i in range(0, len(body), 4))


def holder() -> str:
    civility = random.choice(["M.", "Mme", "M.", "Mme"])
    return f"{civility} {random.choice(FIRST)} {random.choice(LAST).upper()}"


def address() -> str:
    return (
        f"{random.randint(2, 140)} "
        f"{random.choice(['rue', 'avenue', 'boulevard'])} "
        f"{random.choice(['Victor Hugo', 'Jean Jaurès', 'des Lilas', 'Saint-Michel'])}, "
        f"{random.randint(13000, 89000)} {random.choice(CITIES)}"
    )


def classic(idx: int) -> str:
    bank, bic = random.choice(BANKS)
    iban = random_iban()
    name = holder()
    city = random.choice(CITIES)
    branch = random.choice(BRANCHES)
    blocks = [
        "RELEVÉ D'IDENTITÉ BANCAIRE",
        f"Banque : {bank}",
        f"Domiciliation : {branch} — {city}",
        f"Titulaire du compte : {name}",
        f"Adresse du titulaire : {address()}",
        f"IBAN : {iban}",
        f"BIC / SWIFT : {bic}",
        "Ce relevé d'identité bancaire identifie uniquement le compte.",
        "Il ne constitue pas un ordre de virement.",
    ]
    if idx % 2:
        blocks = [blocks[0], blocks[3], blocks[4], blocks[1], blocks[2], blocks[5], blocks[6], blocks[7], blocks[8]]
    return "\n".join(blocks) + "\n"


def codes(idx: int) -> str:
    bank, bic = random.choice(BANKS)
    iban = random_iban()
    compact = iban.replace(" ", "")
    code_banque = compact[4:9]
    code_guichet = compact[9:14]
    compte = compact[14:25]
    cle = compact[25:27]
    name = holder()
    return f"""Relevé d'identité bancaire — {bank}

Titulaire du compte
{name}

Coordonnées du compte
Code banque : {code_banque}
Code guichet : {code_guichet}
Numéro de compte : {compte}
Clé RIB : {cle}

IBAN : {iban}
BIC : {bic}
Domiciliation bancaire : {random.choice(BRANCHES)} {random.choice(CITIES)}

Document destiné à communiquer l'identité du compte à un tiers.
"""


def letter() -> str:
    bank, bic = random.choice(BANKS)
    name = holder()
    iban = random_iban()
    return f"""{bank}

Objet : communication des coordonnées bancaires

Bonjour,

Veuillez trouver ci-dessous le relevé d'identité bancaire du compte
ouvert dans nos livres au nom de {name}.

Titulaire du compte : {name}
Domiciliation : {bank} {random.choice(CITIES)}
IBAN : {iban}
BIC : {bic}

Ces informations suffisent pour créditer le compte par virement.
Conservez ce relevé ; il ne contient pas de numéro de carte.

Service clientèle — {bank}
"""


def compact() -> str:
    bank, bic = random.choice(BANKS)
    return f"""RIB — {bank}

Titulaire : {holder()}
Compte : compte courant particulier
Domiciliation : {random.choice(BRANCHES)}
IBAN {random_iban()}
BIC {bic}

Relevé d'identité bancaire à transmettre pour un virement.
"""


def agency() -> str:
    bank, bic = random.choice(BANKS)
    name = holder()
    return f"""{bank.upper()}
{random.choice(BRANCHES)}

Identité du compte
------------------
Titulaire du compte : {name}
Banque : {bank}
Domiciliation : {random.choice(CITIES)}
IBAN : {random_iban()}
Code BIC : {bic}

Le titulaire autorise la communication de ce relevé d'identité bancaire.
"""


TEMPLATES = (classic, codes, letter, compact, agency)


def generate_one(index: int) -> str:
    template = TEMPLATES[index % len(TEMPLATES)]
    if template in (classic, codes):
        return template(index)
    return template()


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic RIB texts")
    parser.add_argument("--count", type=int, default=35)
    parser.add_argument("--output", type=str, default="./samples/rib")
    parser.add_argument("--seed", type=int, default=20260908)
    args = parser.parse_args()

    random.seed(args.seed)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    for i in range(args.count):
        path = output_dir / f"rib_{i + 1:04d}.txt"
        path.write_text(generate_one(i), encoding="utf-8")
    print(f"Generated {args.count} RIB documents in {output_dir}")


if __name__ == "__main__":
    main()
