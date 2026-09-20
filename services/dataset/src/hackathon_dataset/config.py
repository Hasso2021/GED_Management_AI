from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import yaml

from .models import BuildConfig


def load_config(config_path: Path) -> BuildConfig:
    with config_path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}

    defaults = raw.get("defaults", {})
    output = raw.get("output", {})

    return BuildConfig(
        seed=int(raw.get("seed", 20260317)),
        company_pool_csv=(config_path.parent.parent / defaults.get("company_pool_csv", "inputs/company_pool.csv")).resolve(),
        image_width=int(output.get("image_width", 1654)),
        image_height=int(output.get("image_height", 2339)),
        jpeg_quality=int(output.get("jpeg_quality", 55)),
        payment_terms_days=int(defaults.get("payment_terms_days", 30)),
        tax_rate=Decimal(str(defaults.get("tax_rate", 0.20))),
        currency=str(defaults.get("currency", "EUR")),
        splits={str(split): {str(name): int(count) for name, count in scenarios.items()} for split, scenarios in raw.get("splits", {}).items()},
    )
