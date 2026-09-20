from __future__ import annotations

import csv
import json
from pathlib import Path
from random import Random

from faker import Faker

from .augmentations import apply_quality_profile
from .companies import load_company_pool
from .models import CaseRecord, DocumentRecord
from .rendering import post_process_image, render_document_image, render_document_pdf
from .scenarios import SCENARIOS, create_case_blueprint
from .styles import pick_style

SOURCE_DOCUMENTS_DIR = "source_documents"
REFERENCE_TEXTS_DIR = "reference_texts"
ANNOTATIONS_DIR = "annotations"


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _reference_text_destination(output_root: Path, split: str, case_id: str, doc_id: str) -> Path:
    return output_root / REFERENCE_TEXTS_DIR / split / case_id / f"{doc_id}.txt"


def _source_document_destination(output_root: Path, split: str, case_id: str, doc_id: str, suffix: str) -> Path:
    return output_root / SOURCE_DOCUMENTS_DIR / split / case_id / f"{doc_id}{suffix}"


def _doc_record(
    *,
    doc_id: str,
    case_id: str,
    scenario_id: str,
    split: str,
    doc_type: str,
    file_format: str,
    document_path: str,
    reference_text_path: str,
    quality_profile: str,
    style_id: str,
    supplier_name: str,
    supplier_siret: str,
    supplier_vat: str,
    customer_name: str,
    customer_siret: str,
    invoice_number: str,
    quote_number: str,
    attestation_reference: str,
    issue_date: str,
    due_date: str,
    expiration_date: str,
    currency: str,
    amount_ht: str,
    amount_tva: str,
    amount_ttc: str,
    iban: str,
    bic: str,
    is_forged: bool,
    is_expired: bool,
    has_cross_doc_inconsistency: bool,
    notes: str = "",
) -> DocumentRecord:
    return DocumentRecord(
        doc_id=doc_id,
        case_id=case_id,
        scenario_id=scenario_id,
        split=split,
        doc_type=doc_type,
        file_format=file_format,
        document_path=document_path,
        reference_text_path=reference_text_path,
        quality_profile=quality_profile,
        style_id=style_id,
        supplier_name=supplier_name,
        supplier_siret=supplier_siret,
        supplier_vat=supplier_vat,
        customer_name=customer_name,
        customer_siret=customer_siret,
        invoice_number=invoice_number,
        quote_number=quote_number,
        attestation_reference=attestation_reference,
        issue_date=issue_date,
        due_date=due_date,
        expiration_date=expiration_date,
        currency=currency,
        amount_ht=amount_ht,
        amount_tva=amount_tva,
        amount_ttc=amount_ttc,
        iban=iban,
        bic=bic,
        is_forged=is_forged,
        is_expired=is_expired,
        has_cross_doc_inconsistency=has_cross_doc_inconsistency,
        notes=notes,
    )


def build_dataset(config, output_root: Path) -> dict[str, int]:
    output_root = output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    faker = Faker("fr_FR")
    faker.seed_instance(config.seed)
    rng = Random(config.seed)
    companies = load_company_pool(config.company_pool_csv)

    document_records: list[DocumentRecord] = []
    case_records: list[CaseRecord] = []
    case_index = 1

    for split, scenarios in config.splits.items():
        for scenario_id, count in scenarios.items():
            if scenario_id not in SCENARIOS:
                raise ValueError(f"Scenario inconnu dans la configuration: {scenario_id}")
            for _ in range(count):
                case_id = f"{split}-{case_index:05d}"
                blueprint = create_case_blueprint(
                    scenario_id=scenario_id,
                    index=case_index,
                    rng=rng,
                    fake=faker,
                    companies=companies,
                    config=config,
                )
                package = blueprint["scenario"]
                style = pick_style(rng)
                document_ids: list[str] = []

                for doc_type, content in blueprint["documents"].items():
                    doc_id = f"{case_id}-{doc_type}"
                    suffix = ".pdf" if package.file_format == "pdf" else f".{package.file_format}"
                    document_path = _source_document_destination(output_root, split, case_id, doc_id, suffix)
                    reference_text_path = _reference_text_destination(output_root, split, case_id, doc_id)
                    reference_text_path.parent.mkdir(parents=True, exist_ok=True)

                    if package.file_format == "pdf":
                        render_document_pdf(content, document_path, style)
                    else:
                        render_document_image(content, document_path, config.image_width, config.image_height, style)
                        post_process_image(document_path)
                        apply_quality_profile(document_path, package.quality_profile, config.jpeg_quality, rng)

                    reference_text_path.write_text(content.as_text(), encoding="utf-8")
                    document_ids.append(doc_id)

                    document_records.append(
                        _doc_record(
                            doc_id=doc_id,
                            case_id=case_id,
                            scenario_id=scenario_id,
                            split=split,
                            doc_type=doc_type,
                            file_format=package.file_format,
                            document_path=str(document_path.relative_to(output_root)).replace("\\", "/"),
                            reference_text_path=str(reference_text_path.relative_to(output_root)).replace("\\", "/"),
                            quality_profile=package.quality_profile,
                            style_id=style.style_id,
                            supplier_name=content.supplier.company_name,
                            supplier_siret=content.supplier.siret,
                            supplier_vat=content.supplier.vat_number,
                            customer_name=content.customer.company_name,
                            customer_siret=content.customer.siret,
                            invoice_number=content.invoice_number,
                            quote_number=content.quote_number,
                            attestation_reference=content.attestation_reference,
                            issue_date=content.issue_date,
                            due_date=content.due_date,
                            expiration_date=content.expiration_date,
                            currency=content.currency,
                            amount_ht=f"{content.amount_ht:.2f}",
                            amount_tva=f"{content.amount_tva:.2f}",
                            amount_ttc=f"{content.amount_ttc:.2f}",
                            iban=content.iban,
                            bic=content.bic,
                            is_forged=package.is_forged,
                            is_expired=package.is_expired,
                            has_cross_doc_inconsistency=package.has_cross_doc_inconsistency,
                            notes=" | ".join(content.notes),
                        )
                    )

                case_records.append(
                    CaseRecord(
                        case_id=case_id,
                        scenario_id=scenario_id,
                        split=split,
                        document_ids=document_ids,
                        expected_consistency_status=package.expected_status,
                        expected_issues=list(package.expected_issues),
                    )
                )
                case_index += 1

    document_rows = [record.to_dict() for record in document_records]
    case_rows = [record.to_dict() for record in case_records]
    annotations = output_root / ANNOTATIONS_DIR
    _write_jsonl(annotations / "documents.jsonl", document_rows)
    _write_jsonl(annotations / "cases.jsonl", case_rows)
    _write_csv(annotations / "documents.csv", document_rows)
    _write_csv(annotations / "cases.csv", case_rows)

    summary = {
        "documents": len(document_records),
        "cases": len(case_records),
        "splits": {
            split: sum(1 for row in case_rows if row["split"] == split)
            for split in sorted({row["split"] for row in case_rows})
        },
    }
    (annotations / "build_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary
