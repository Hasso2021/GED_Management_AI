# Hackathon Dataset Corpus

This branch keeps only two things:

- the generated document corpus tracked in `generated/training_corpus/`
- the Python code and config used to build that corpus again

## Structure

```text
configs/
generated/training_corpus/
inputs/
scripts/
src/hackathon_dataset/
```

## Prerequisites

```powershell
py -3.14 -m pip install -r requirements.txt
```

## 1. Prepare the company registry

Download a SIRENE CSV export, then run:

```powershell
py -3.14 scripts\dataset_cli.py prepare-companies `
  --input path\to\sirene.csv `
  --output inputs\company_pool.csv `
  --limit 500
```

This step filters active companies, rebuilds usable names, computes a French VAT number from the SIREN, and writes the lightweight registry consumed by the generator.

## 2. Build the corpus

```powershell
py -3.14 scripts\dataset_cli.py build-dataset `
  --config configs\dataset_config.yaml `
  --output generated\training_corpus
```

Output layout:

```text
generated/training_corpus/
  source_documents/
    train|validation|test/
  reference_texts/
    train|validation|test/
  annotations/
    documents.jsonl
    cases.jsonl
    documents.csv
    cases.csv
    build_summary.json
```

- `source_documents/`: rendered PDFs, PNGs, and JPGs used as model inputs
- `reference_texts/`: reference text written for each generated document
- `annotations/`: labels and case-level metadata

## Implemented scenarios

- `legitimate_pdf`
- `legitimate_scan`
- `legitimate_smartphone`
- `forged_amount_pdf`
- `forged_identifier_scan`
- `invoice_quote_mismatch`
- `expired_attestation`
- `attestation_siret_mismatch`
- `rib_mismatch`
- `missing_field_scan`

Each scenario generates one `case_id`, one or more documents, and an expected consistency outcome such as `coherent`, `amount_mismatch`, `siret_mismatch`, or `expired_attestation`.

## Annotation files

`annotations/documents.jsonl` contains one record per document with:

- identifiers: `doc_id`, `case_id`, `split`
- file metadata: `doc_type`, `file_format`, `document_path`, `reference_text_path`
- business labels: `supplier_*`, `customer_*`, `invoice_number`, dates, amounts
- quality flags: `quality_profile`, `is_forged`, `is_expired`, `has_cross_doc_inconsistency`

`annotations/cases.jsonl` contains one record per case with:

- `case_id`
- `scenario_id`
- `split`
- `document_ids`
- `expected_consistency_status`
- `expected_issues`
