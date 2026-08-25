import json
from datetime import date
from decimal import Decimal
from pathlib import Path

from zwapgrid.client import invoice_date_param
from zwapgrid.parse import parse_cash_row, parse_identity, parse_payment
from zwapgrid.remittance import build_needles, needles_match_haystack

FIXTURES = Path(__file__).parent / "fixtures"


def _load(relative: str) -> dict:
    return json.loads((FIXTURES / relative).read_text())


def test_invoice_date_param_strips_time():
    assert invoice_date_param("2025-08-25T00:00:00Z") == "2025-08-25"
    assert invoice_date_param("2025-08-25") == "2025-08-25"
    assert invoice_date_param(None) is None


def test_parse_identity_orgnr_and_usable_iban():
    facts = parse_identity(_load("identity/companyinformation.json"))
    assert facts.legal_name == "Nordic Retail Group AB"
    assert facts.organization_number and facts.organization_number.id == "559123-4567"
    assert facts.organization_number.scheme_id == "SE:ORGNR"
    assert facts.address and facts.address.city == "Stockholm"
    usable = [b for b in facts.bank_accounts if b.usable]
    unused = [b for b in facts.bank_accounts if not b.usable]
    assert any(b.normalized.startswith("SE45") for b in usable)
    assert unused and unused[0].raw_id == "5233"
    assert facts.bank_accounts_unusable is False


def test_unpaid_invoice_is_not_match_eligible():
    invoice = _load("money_in/sales_invoice_unpaid.json")
    row = parse_cash_row(invoice, [], direction="inbound")
    assert row.paid is False
    assert row.match_eligible is False
    assert row.cash_amount is None
    assert needles_match_haystack(row.remittance_needles, "BETALNING INV-001")


def test_seed_fully_paid_uses_tax_inclusive_not_remaining():
    invoice = _load("money_in/sales_invoice_seed.json")
    row = parse_cash_row(invoice, [], direction="inbound")
    assert row.paid is True
    assert row.cash_amount == Decimal("3281.00")
    assert row.remaining == Decimal("-0.25")
    assert row.cash_date == date(2026, 8, 25)
    assert "1" not in row.remittance_needles
    assert row.normalized_counterparty == "NORDIC RETAIL GROUP"


def test_payment_needles_and_pay59_match_ais_remittance():
    payment = _load("money_in/zwapgrid_payment.json")["data"][0]
    invoice = _load("money_in/sales_invoice_unpaid.json")
    invoice["paymentStatus"] = {"status": "PAID"}
    row = parse_cash_row(invoice, [payment], direction="inbound")
    assert row.cash_amount == Decimal("500")
    assert row.currency == "DKK"
    assert row.cash_date == date(2022, 6, 1)
    haystack = _load("money_in/ais_transaction.json")["remittanceInformationUnstructured"]
    assert needles_match_haystack(row.remittance_needles, haystack)


def test_supplier_seed_reference_is_a_needle():
    invoice = _load("money_out/supplier_seed.json")
    row = parse_cash_row(invoice, [], direction="outbound")
    assert row.paid is True
    assert row.cash_amount == Decimal("2687.50")
    assert any("ZG" in n and "SEED" in n for n in row.remittance_needles)
    assert needles_match_haystack(row.remittance_needles, "ZG-SEED-ACME-SUP-01")
    assert row.normalized_counterparty == "CLOUDLANE SYSTEMS"


def test_remittance_rules():
    needles = build_needles("INV-001", "1234-567890")
    assert needles_match_haystack(needles, "BETALNING INV-001 ACME")
    assert needles_match_haystack(needles, "OCR 1234-567890")
    assert not needles_match_haystack(build_needles("INV-001"), "001")
    assert "1" not in build_needles("1")
    parsed = parse_payment(_load("money_in/zwapgrid_payment.json")["data"][0])
    assert parsed.billing_invoice_ids == ["INV-001"]
    assert parsed.ledger_account_ref == "5233"
