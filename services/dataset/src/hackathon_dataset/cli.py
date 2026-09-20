from __future__ import annotations

import argparse
import json
from pathlib import Path

from .builder import build_dataset
from .companies import normalize_sirene_csv
from .config import load_config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Hackathon training corpus builder")
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser("prepare-companies", help="Normalise un export SIRENE")
    prepare.add_argument("--input", required=True, type=Path, help="Chemin vers le CSV SIRENE")
    prepare.add_argument("--output", required=True, type=Path, help="Chemin du company_pool de sortie")
    prepare.add_argument("--limit", type=int, default=500, help="Nombre max de lignes retenues")

    build = subparsers.add_parser("build-dataset", help="Genere le corpus documente")
    build.add_argument("--config", required=True, type=Path, help="Chemin du YAML de configuration")
    build.add_argument("--output", required=True, type=Path, help="Dossier de sortie")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "prepare-companies":
        written = normalize_sirene_csv(args.input, args.output, args.limit)
        print(json.dumps({"written_companies": written, "output": str(args.output.resolve())}, ensure_ascii=False))
        return 0

    if args.command == "build-dataset":
        config = load_config(args.config.resolve())
        summary = build_dataset(config, args.output.resolve())
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return 0

    parser.error(f"Commande non supportee: {args.command}")
    return 2
