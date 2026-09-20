# dataset

Synthetic French administrative document generators.

## Quick start

```bash
chmod +x generate_dataset.sh
./generate_dataset.sh ./samples
```

## Generators

| Script | Output | Count |
|--------|--------|-------|
| `generate_invoices.py --type FACTURE` | Factures with valid SIRET/TVA/amounts | 50 |
| `generate_invoices.py --type DEVIS` | Devis | 20 |
| `generate_siret.py --type SIRET_ATTESTATION` | INSEE SIRENE attestations | 20 |
| `generate_siret.py --type KBIS` | Extrait KBIS | 20 |
| `generate_noise.py` | Noisy OCR variants | varies |

## Validation guarantees

All generated documents satisfy:
- SIRET: 14 digits with valid Luhn checksum
- TVA: `FR` + 2-digit key + SIREN
- Amounts: HT × (1 + tva_rate/100) = TTC (exact)
