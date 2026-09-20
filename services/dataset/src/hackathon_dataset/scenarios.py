from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
from random import Random

from faker import Faker

from .models import BuildConfig, Company, DocumentContent


TWOPLACES = Decimal("0.01")


@dataclass(slots=True)
class ScenarioPackage:
    scenario_id: str
    doc_types: list[str]
    expected_status: str
    expected_issues: list[str]
    quality_profile: str
    file_format: str
    is_forged: bool = False
    has_cross_doc_inconsistency: bool = False
    is_expired: bool = False
    missing_field: str = ""


SCENARIOS: dict[str, ScenarioPackage] = {
    "legitimate_pdf": ScenarioPackage(
        scenario_id="legitimate_pdf",
        doc_types=["invoice"],
        expected_status="coherent",
        expected_issues=[],
        quality_profile="clean_pdf",
        file_format="pdf",
    ),
    "legitimate_scan": ScenarioPackage(
        scenario_id="legitimate_scan",
        doc_types=["invoice"],
        expected_status="coherent",
        expected_issues=[],
        quality_profile="scan_blur_rotation",
        file_format="png",
    ),
    "legitimate_smartphone": ScenarioPackage(
        scenario_id="legitimate_smartphone",
        doc_types=["invoice"],
        expected_status="coherent",
        expected_issues=[],
        quality_profile="smartphone_photo",
        file_format="jpg",
    ),
    "forged_amount_pdf": ScenarioPackage(
        scenario_id="forged_amount_pdf",
        doc_types=["invoice"],
        expected_status="amount_mismatch",
        expected_issues=["forged_amount"],
        quality_profile="clean_pdf",
        file_format="pdf",
        is_forged=True,
    ),
    "forged_identifier_scan": ScenarioPackage(
        scenario_id="forged_identifier_scan",
        doc_types=["invoice"],
        expected_status="siret_mismatch",
        expected_issues=["forged_supplier_identifier"],
        quality_profile="pixelated_scan",
        file_format="png",
        is_forged=True,
    ),
    "invoice_quote_mismatch": ScenarioPackage(
        scenario_id="invoice_quote_mismatch",
        doc_types=["quote", "invoice"],
        expected_status="amount_mismatch",
        expected_issues=["quote_invoice_amount_gap"],
        quality_profile="clean_pdf",
        file_format="pdf",
        has_cross_doc_inconsistency=True,
    ),
    "expired_attestation": ScenarioPackage(
        scenario_id="expired_attestation",
        doc_types=["invoice", "attestation"],
        expected_status="expired_attestation",
        expected_issues=["attestation_expired"],
        quality_profile="clean_pdf",
        file_format="pdf",
        is_expired=True,
        has_cross_doc_inconsistency=True,
    ),
    "attestation_siret_mismatch": ScenarioPackage(
        scenario_id="attestation_siret_mismatch",
        doc_types=["invoice", "attestation"],
        expected_status="siret_mismatch",
        expected_issues=["attestation_supplier_siret_mismatch"],
        quality_profile="scan_blur_rotation",
        file_format="png",
        has_cross_doc_inconsistency=True,
    ),
    "rib_mismatch": ScenarioPackage(
        scenario_id="rib_mismatch",
        doc_types=["invoice", "rib"],
        expected_status="rib_mismatch",
        expected_issues=["rib_supplier_name_mismatch"],
        quality_profile="clean_pdf",
        file_format="pdf",
        has_cross_doc_inconsistency=True,
    ),
    "missing_field_scan": ScenarioPackage(
        scenario_id="missing_field_scan",
        doc_types=["invoice"],
        expected_status="missing_field",
        expected_issues=["missing_due_date"],
        quality_profile="low_contrast_scan",
        file_format="png",
        missing_field="due_date",
    ),
}


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def _line_item(description: str, quantity: int, unit_price: Decimal) -> dict[str, object]:
    line_total = _quantize(Decimal(quantity) * unit_price)
    return {
        "description": description,
        "quantity": quantity,
        "unit_price": _quantize(unit_price),
        "line_total": line_total,
    }


def _make_iban(rng: Random) -> str:
    digits = "".join(str(rng.randint(0, 9)) for _ in range(23))
    return f"FR76{digits}"


def _make_bic(rng: Random) -> str:
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    return "".join(rng.choice(alphabet) for _ in range(8))


def _pick_counterparty(rng: Random, companies: list[Company], forbidden_siret: str) -> Company:
    candidates = [company for company in companies if company.siret != forbidden_siret]
    return rng.choice(candidates)


def _line_items(fake: Faker, rng: Random) -> list[dict[str, object]]:
    entries = []
    for _ in range(rng.randint(2, 4)):
        entries.append(
            _line_item(
                description=fake.bs().replace("e-enable", "digitaliser").title(),
                quantity=rng.randint(1, 5),
                unit_price=_quantize(Decimal(str(rng.uniform(80, 1500)))),
            )
        )
    return entries


def _totals(line_items: list[dict[str, object]], tax_rate: Decimal) -> tuple[Decimal, Decimal, Decimal]:
    amount_ht = _quantize(sum((item["line_total"] for item in line_items), Decimal("0.00")))
    amount_tva = _quantize(amount_ht * tax_rate)
    amount_ttc = _quantize(amount_ht + amount_tva)
    return amount_ht, amount_tva, amount_ttc


def create_case_blueprint(
    scenario_id: str,
    index: int,
    rng: Random,
    fake: Faker,
    companies: list[Company],
    config: BuildConfig,
) -> dict[str, object]:
    scenario = SCENARIOS[scenario_id]
    supplier = rng.choice(companies)
    customer = _pick_counterparty(rng, companies, supplier.siret)
    issue_dt = fake.date_between(start_date="-240d", end_date="-2d")
    due_dt = issue_dt + timedelta(days=config.payment_terms_days)
    expiration_dt = due_dt + timedelta(days=90)
    line_items = _line_items(fake, rng)
    amount_ht, amount_tva, amount_ttc = _totals(line_items, config.tax_rate)
    invoice_number = f"FAC-{issue_dt.strftime('%Y%m')}-{index:04d}"
    quote_number = f"DEV-{issue_dt.strftime('%Y%m')}-{index:04d}"
    attestation_reference = f"ATTEST-{issue_dt.strftime('%Y%m')}-{index:04d}"
    iban = _make_iban(rng)
    bic = _make_bic(rng)

    notes: list[str] = []
    document_payloads: dict[str, DocumentContent] = {}

    quote_amount_ht = amount_ht
    quote_amount_tva = amount_tva
    quote_amount_ttc = amount_ttc

    if scenario_id == "forged_amount_pdf":
        amount_ttc = _quantize(amount_ttc + Decimal("149.99"))
        notes.append("Montant TTC incoherent avec le detail des lignes.")
    elif scenario_id == "forged_identifier_scan":
        supplier = Company(
            company_name=supplier.company_name,
            siret=supplier.siret[:-1] + str((int(supplier.siret[-1]) + 3) % 10),
            vat_number=supplier.vat_number,
            address_line_1=supplier.address_line_1,
            address_line_2=supplier.address_line_2,
            postal_code=supplier.postal_code,
            city=supplier.city,
            country=supplier.country,
            naf_code=supplier.naf_code,
        )
        notes.append("Identifiant fournisseur potentiellement falsifie.")
    elif scenario_id == "invoice_quote_mismatch":
        quote_amount_ttc = _quantize(amount_ttc - Decimal("220.00"))
        quote_amount_ht = _quantize(quote_amount_ttc / (Decimal("1.00") + config.tax_rate))
        quote_amount_tva = _quantize(quote_amount_ttc - quote_amount_ht)
        notes.append("Le devis et la facture n'ont pas le meme montant.")
    elif scenario_id == "expired_attestation":
        expiration_dt = issue_dt - timedelta(days=8)
        notes.append("Attestation hors validite.")
    elif scenario_id == "missing_field_scan":
        notes.append("La date d'echeance est absente du document.")

    document_payloads["invoice"] = DocumentContent(
        doc_type="invoice",
        title="FACTURE FOURNISSEUR",
        supplier=supplier,
        customer=customer,
        issue_date=issue_dt.isoformat(),
        due_date="" if scenario.missing_field == "due_date" else due_dt.isoformat(),
        expiration_date="",
        invoice_number=invoice_number,
        quote_number="",
        attestation_reference="",
        iban=iban,
        bic=bic,
        currency=config.currency,
        amount_ht=amount_ht,
        amount_tva=amount_tva,
        amount_ttc=amount_ttc,
        line_items=line_items,
        notes=list(notes),
    )

    if "quote" in scenario.doc_types:
        document_payloads["quote"] = DocumentContent(
            doc_type="quote",
            title="DEVIS",
            supplier=supplier,
            customer=customer,
            issue_date=(issue_dt - timedelta(days=6)).isoformat(),
            due_date=(issue_dt + timedelta(days=24)).isoformat(),
            expiration_date="",
            invoice_number="",
            quote_number=quote_number,
            attestation_reference="",
            iban="",
            bic="",
            currency=config.currency,
            amount_ht=quote_amount_ht,
            amount_tva=quote_amount_tva,
            amount_ttc=quote_amount_ttc,
            line_items=line_items,
            notes=["Devis commercial lie a la facture.", *notes],
        )

    if "attestation" in scenario.doc_types:
        attestation_supplier = supplier
        if scenario_id == "attestation_siret_mismatch":
            alt_supplier = _pick_counterparty(rng, companies, supplier.siret)
            attestation_supplier = Company(
                company_name=supplier.company_name,
                siret=alt_supplier.siret,
                vat_number=alt_supplier.vat_number,
                address_line_1=supplier.address_line_1,
                address_line_2=supplier.address_line_2,
                postal_code=supplier.postal_code,
                city=supplier.city,
                country=supplier.country,
                naf_code=supplier.naf_code,
            )
        document_payloads["attestation"] = DocumentContent(
            doc_type="attestation",
            title="ATTESTATION DE VIGILANCE",
            supplier=attestation_supplier,
            customer=customer,
            issue_date=issue_dt.isoformat(),
            due_date="",
            expiration_date=expiration_dt.isoformat(),
            invoice_number="",
            quote_number="",
            attestation_reference=attestation_reference,
            iban="",
            bic="",
            currency=config.currency,
            amount_ht=Decimal("0.00"),
            amount_tva=Decimal("0.00"),
            amount_ttc=Decimal("0.00"),
            line_items=[],
            notes=["Document de conformite pour verification fournisseur.", *notes],
        )

    if "rib" in scenario.doc_types:
        rib_supplier = supplier
        if scenario_id == "rib_mismatch":
            alt_supplier = _pick_counterparty(rng, companies, supplier.siret)
            rib_supplier = Company(
                company_name=alt_supplier.company_name,
                siret=supplier.siret,
                vat_number=supplier.vat_number,
                address_line_1=supplier.address_line_1,
                address_line_2=supplier.address_line_2,
                postal_code=supplier.postal_code,
                city=supplier.city,
                country=supplier.country,
                naf_code=supplier.naf_code,
            )
        document_payloads["rib"] = DocumentContent(
            doc_type="rib",
            title="RELEVE D'IDENTITE BANCAIRE",
            supplier=rib_supplier,
            customer=customer,
            issue_date=issue_dt.isoformat(),
            due_date="",
            expiration_date="",
            invoice_number="",
            quote_number="",
            attestation_reference="",
            iban=iban,
            bic=bic,
            currency=config.currency,
            amount_ht=Decimal("0.00"),
            amount_tva=Decimal("0.00"),
            amount_ttc=Decimal("0.00"),
            line_items=[],
            notes=["Coordonnees bancaires fournisseur.", *notes],
        )

    return {
        "scenario": scenario,
        "documents": document_payloads,
    }
