from __future__ import annotations

from dataclasses import asdict, dataclass, field
from decimal import Decimal
from pathlib import Path


@dataclass(slots=True)
class Company:
    company_name: str
    siret: str
    vat_number: str
    address_line_1: str
    address_line_2: str
    postal_code: str
    city: str
    country: str
    naf_code: str = ""

    def address_lines(self) -> list[str]:
        lines = [self.address_line_1.strip()]
        if self.address_line_2.strip():
            lines.append(self.address_line_2.strip())
        lines.append(f"{self.postal_code.strip()} {self.city.strip()}".strip())
        if self.country.strip():
            lines.append(self.country.strip())
        return [line for line in lines if line]


@dataclass(slots=True)
class CaseRecord:
    case_id: str
    scenario_id: str
    split: str
    document_ids: list[str]
    expected_consistency_status: str
    expected_issues: list[str]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class DocumentRecord:
    doc_id: str
    case_id: str
    scenario_id: str
    split: str
    doc_type: str
    file_format: str
    document_path: str
    reference_text_path: str
    quality_profile: str
    style_id: str
    supplier_name: str
    supplier_siret: str
    supplier_vat: str
    customer_name: str
    customer_siret: str
    invoice_number: str
    quote_number: str
    attestation_reference: str
    issue_date: str
    due_date: str
    expiration_date: str
    currency: str
    amount_ht: str
    amount_tva: str
    amount_ttc: str
    iban: str
    bic: str
    is_forged: bool
    is_expired: bool
    has_cross_doc_inconsistency: bool
    notes: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class DocumentContent:
    doc_type: str
    title: str
    supplier: Company
    customer: Company
    issue_date: str
    due_date: str
    expiration_date: str
    invoice_number: str
    quote_number: str
    attestation_reference: str
    iban: str
    bic: str
    currency: str
    amount_ht: Decimal
    amount_tva: Decimal
    amount_ttc: Decimal
    line_items: list[dict[str, object]]
    notes: list[str] = field(default_factory=list)

    def as_text(self) -> str:
        text_lines = [
            self.title,
            "",
            f"Fournisseur: {self.supplier.company_name}",
            f"SIRET: {self.supplier.siret}",
            f"TVA: {self.supplier.vat_number}",
            f"Client: {self.customer.company_name}",
            f"SIRET client: {self.customer.siret}",
        ]
        if self.invoice_number:
            text_lines.append(f"Numero facture: {self.invoice_number}")
        if self.quote_number:
            text_lines.append(f"Numero devis: {self.quote_number}")
        if self.attestation_reference:
            text_lines.append(f"Reference attestation: {self.attestation_reference}")
        if self.issue_date:
            text_lines.append(f"Date emission: {self.issue_date}")
        if self.due_date:
            text_lines.append(f"Date echeance: {self.due_date}")
        if self.expiration_date:
            text_lines.append(f"Date expiration: {self.expiration_date}")
        if self.iban:
            text_lines.append(f"IBAN: {self.iban}")
        if self.bic:
            text_lines.append(f"BIC: {self.bic}")
        if self.doc_type in {"invoice", "quote"}:
            text_lines.extend(
                [
                    f"Montant HT: {self.amount_ht:.2f} {self.currency}",
                    f"Montant TVA: {self.amount_tva:.2f} {self.currency}",
                    f"Montant TTC: {self.amount_ttc:.2f} {self.currency}",
                    "",
                    "Lignes:",
                ]
            )
            for item in self.line_items:
                text_lines.append(
                    "- {description} | qty={quantity} | pu={unit_price:.2f} | total={line_total:.2f}".format(
                        **item
                    )
                )
        if self.notes:
            text_lines.extend(["", "Notes:"])
            text_lines.extend(f"- {note}" for note in self.notes)
        return "\n".join(text_lines)


@dataclass(slots=True)
class BuildConfig:
    seed: int
    company_pool_csv: Path
    image_width: int
    image_height: int
    jpeg_quality: int
    payment_terms_days: int
    tax_rate: Decimal
    currency: str
    splits: dict[str, dict[str, int]]
