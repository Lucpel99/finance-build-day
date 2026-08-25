from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, InvalidOperation

from .models import (
    AddressFacts,
    BankAccountFact,
    CashRow,
    Identifier,
    IdentityFacts,
    PaymentFact,
)
from .remittance import build_needles, digits_only, normalize

_LEGAL_SUFFIXES = {
    "AB",
    "AS",
    "A/S",
    "LTD",
    "LLC",
    "GMBH",
    "OY",
    "NV",
    "SA",
    "INC",
    "CORP",
    "CO",
    "PLC",
    "APS",
    "KB",
}
_PAID_STATUSES = {"paid", "fully_paid", "fullypaid"}
_REVENUE_KEYWORDS = (
    "revenue",
    "net sales",
    "sales",
    "omsättning",
    "intäkt",
    "intakt",
    "turnover",
    "net revenue",
    "rörelsens intäkter",
)


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    text = str(value).strip()[:10]
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def parse_decimal(value) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def amount_pair(obj: dict | None) -> tuple[Decimal | None, str | None]:
    if not obj or not isinstance(obj, dict):
        return None, None
    return parse_decimal(obj.get("amount")), obj.get("currencyId") or obj.get("currency")


def nested(obj: dict | None, *keys: str):
    current = obj
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def identifier_from(obj: dict | None) -> Identifier | None:
    if not obj or not isinstance(obj, dict):
        return None
    ident = Identifier(id=obj.get("id"), scheme_id=obj.get("schemeId"))
    if ident.id or ident.scheme_id:
        return ident
    return None


def normalize_counterparty(name: str | None) -> str | None:
    folded = normalize(name)
    if not folded:
        return None
    folded = re.sub(r"\bSEED\b", " ", folded)
    tokens = [tok for tok in folded.split() if tok not in _LEGAL_SUFFIXES]
    result = " ".join(tokens).strip()
    return result or folded


def status_key(status: str | None) -> str:
    if not status:
        return ""
    return status.lower().replace(" ", "_").replace("-", "_")


def is_paid(status: str | None) -> bool:
    return status_key(status) in _PAID_STATUSES


def is_usable_account_id(raw: str) -> bool:
    compact = re.sub(r"[\s-]", "", raw).upper()
    if len(compact) >= 15 and compact[:2].isalpha() and compact[2:].isalnum():
        return True
    digits = digits_only(compact)
    return len(digits) >= 8


def party_name(party: dict | None) -> str | None:
    if not party:
        return None
    name = nested(party, "partyName", "name")
    if name:
        return name
    legal = nested(party, "partyLegalEntity", "registrationName")
    return legal


def collect_payment_ids(invoice: dict) -> list[str]:
    found: list[str] = []
    for means in invoice.get("paymentMeans") or []:
        if not isinstance(means, dict):
            continue
        ids = means.get("paymentIds") or []
        if isinstance(ids, list):
            found.extend(str(item) for item in ids if item)
        elif ids:
            found.append(str(ids))
        account = means.get("financialAccount") or {}
        if isinstance(account, dict) and account.get("id"):
            found.append(str(account["id"]))
    return found


def parse_identity(payload: dict) -> IdentityFacts:
    legal = nested(payload, "partyLegalEntity") or {}
    org = identifier_from(legal.get("companyId") if isinstance(legal, dict) else None)
    extras: list[Identifier] = []
    for item in payload.get("partyIdentification") or []:
        ident = identifier_from(item)
        if ident:
            extras.append(ident)
    if org is None:
        for ident in extras:
            if ident.scheme_id and "ORG" in ident.scheme_id.upper():
                org = ident
                break

    address_obj = payload.get("postalAddress") or {}
    country = address_obj.get("country") or {}
    address = AddressFacts(
        street=address_obj.get("streetName"),
        building=address_obj.get("buildingNumber"),
        postal_code=address_obj.get("postalZone"),
        city=address_obj.get("cityName"),
        country_code=country.get("identificationCode") if isinstance(country, dict) else None,
    )

    banks: list[BankAccountFact] = []
    for means in payload.get("paymentMeans") or []:
        if not isinstance(means, dict):
            continue
        account = means.get("financialAccount") or {}
        raw = None
        institution = None
        if isinstance(account, dict):
            raw = account.get("id")
            institution = account.get("financialInstitution")
        if not raw:
            raw = means.get("payeeFinancialAccount")
        if not raw:
            continue
        raw_id = str(raw)
        banks.append(
            BankAccountFact(
                raw_id=raw_id,
                normalized=re.sub(r"[\s-]", "", raw_id).upper(),
                institution=institution,
                usable=is_usable_account_id(raw_id),
            )
        )

    usable = [b for b in banks if b.usable]
    return IdentityFacts(
        legal_name=(legal.get("registrationName") if isinstance(legal, dict) else None)
        or nested(payload, "partyName", "name"),
        trading_name=nested(payload, "partyName", "name"),
        organization_number=org,
        other_identifiers=extras,
        address=address if any(v for v in address.model_dump().values()) else None,
        phone=payload.get("phone"),
        email=payload.get("email"),
        bank_accounts=banks,
        bank_accounts_unusable=bool(banks) and not usable,
    )


def parse_payment(payload: dict) -> PaymentFact:
    currency = None
    doc = payload.get("documentCurrencyCode") or {}
    if isinstance(doc, dict):
        currency = doc.get("currencyId") or doc.get("currency")
    credit, credit_ccy = amount_pair(payload.get("creditAmount"))
    amount = parse_decimal(payload.get("amount"))
    if amount is None:
        amount = credit
    if not currency:
        currency = credit_ccy

    billing_ids: list[str] = []
    for ref in payload.get("billingReferences") or []:
        if not isinstance(ref, dict):
            continue
        for ident in ref.get("invoiceDocumentReferences") or []:
            if isinstance(ident, dict) and ident.get("id"):
                billing_ids.append(str(ident["id"]))

    account = payload.get("accountingAccount") or {}
    return PaymentFact(
        id=payload.get("id") or payload.get("paymentId"),
        reference=payload.get("reference"),
        amount=amount,
        currency=currency,
        paid_date=parse_date(payload.get("paidDate")),
        received_date=parse_date(payload.get("receivedDate")),
        booked_date=parse_date(payload.get("bookedDate")),
        booked=payload.get("bookedIndicator"),
        billing_invoice_ids=billing_ids,
        ledger_account_ref=(account.get("reference") or account.get("id"))
        if isinstance(account, dict)
        else None,
        ledger_account_name=account.get("name") if isinstance(account, dict) else None,
    )


def _party_from_invoice(invoice: dict, direction: str) -> str | None:
    if direction == "inbound":
        party = nested(invoice, "accountingCustomerParty", "party")
    else:
        party = nested(invoice, "accountingSupplierParty", "party")
    return party_name(party)


def parse_cash_row(
    invoice: dict,
    payments: list[dict],
    *,
    direction: str,
    extra_needles: list[str] | None = None,
) -> CashRow:
    status_obj = invoice.get("paymentStatus") or {}
    status = status_obj.get("status") if isinstance(status_obj, dict) else None
    tax_inc, ccy = amount_pair(nested(invoice, "legalMonetaryTotal", "taxInclusiveAmount"))
    payable, payable_ccy = amount_pair(nested(invoice, "legalMonetaryTotal", "payableAmount"))
    remaining, rem_ccy = amount_pair(invoice.get("totalBalanceAmount"))
    currency = ccy or payable_ccy or rem_ccy

    credit = nested(invoice, "creditInvoice") or {}
    credit_note = bool(
        credit.get("creditInvoiceIndicator") if isinstance(credit, dict) else False
    )
    cancelled = bool(invoice.get("cancelledInvoiceIndicator"))
    paid = is_paid(status) or bool(payments)

    parsed_payments = [parse_payment(item) for item in payments]
    cash_amount = None
    cash_currency = currency
    cash_date = None
    cash_source = None
    if parsed_payments:
        amounts = [p.amount for p in parsed_payments if p.amount is not None]
        if amounts:
            cash_amount = sum(amounts, Decimal("0"))
        cash_currency = next((p.currency for p in parsed_payments if p.currency), currency)
        for payment in parsed_payments:
            for source, value in (
                ("paid", payment.paid_date),
                ("received", payment.received_date),
                ("booked", payment.booked_date),
            ):
                if value:
                    cash_date = value
                    cash_source = source
                    break
            if cash_date:
                break
    elif paid:
        cash_amount = tax_inc or payable
        cash_date = parse_date(status_obj.get("settlementDate")) if isinstance(status_obj, dict) else None
        cash_source = "settlement" if cash_date else None

    needles = build_needles(
        invoice.get("reference"),
        invoice.get("id") if invoice.get("id") != invoice.get("reference") else None,
        *(p.reference for p in parsed_payments),
        *(bid for p in parsed_payments for bid in p.billing_invoice_ids),
        *(extra_needles or []),
    )

    eligible = paid and not cancelled and not credit_note
    counterparty = _party_from_invoice(invoice, direction)

    return CashRow(
        direction=direction,  # type: ignore[arg-type]
        invoice_id=invoice.get("id"),
        invoice_reference=invoice.get("reference") or invoice.get("id"),
        counterparty=counterparty,
        normalized_counterparty=normalize_counterparty(counterparty),
        issue_date=parse_date(invoice.get("issueDate")),
        due_date=parse_date(invoice.get("dueDate")),
        settlement_date=parse_date(status_obj.get("settlementDate"))
        if isinstance(status_obj, dict)
        else None,
        status=status,
        paid=paid,
        cancelled=cancelled,
        credit_note=credit_note,
        tax_inclusive=tax_inc,
        remaining=remaining,
        currency=cash_currency,
        cash_amount=cash_amount,
        cash_date=cash_date,
        cash_date_source=cash_source,
        remittance_needles=needles,
        payments=parsed_payments,
        match_eligible=eligible,
    )


def walk_report_amounts(node: dict, prefix: str = "") -> list[tuple[str, Decimal, str | None]]:
    found: list[tuple[str, Decimal, str | None]] = []
    descriptions = node.get("descriptions") or []
    labels = []
    for desc in descriptions:
        if isinstance(desc, dict) and desc.get("text"):
            labels.append(str(desc["text"]))
    label = " / ".join(labels) or prefix

    balance = node.get("balance") or {}
    for base in (balance.get("baseCurrencies") or []) if isinstance(balance, dict) else []:
        if not isinstance(base, dict):
            continue
        amount = parse_decimal(base.get("baseAmount"))
        if amount is None:
            continue
        found.append((label, amount, base.get("currencyId")))

    for child in node.get("subCategories") or []:
        if isinstance(child, dict):
            found.extend(walk_report_amounts(child, label))
    for account in node.get("accounts") or []:
        if isinstance(account, dict):
            found.extend(walk_report_amounts(account, label))
    return found


def extract_revenue(statement: dict) -> tuple[Decimal | None, Decimal | None, str | None]:
    """Return (revenue, profit_loss, currency)."""
    profit = None
    currency = None
    pnl = statement.get("profitLossBalance") or {}
    for base in (pnl.get("baseCurrencies") or []) if isinstance(pnl, dict) else []:
        if isinstance(base, dict):
            profit = parse_decimal(base.get("baseAmount"))
            currency = base.get("currencyId")
            break

    report = statement.get("financialReport") or {}
    categories = report.get("categories") or []
    revenue = None
    for category in categories:
        if not isinstance(category, dict):
            continue
        rows = walk_report_amounts(category)
        label = " ".join(r[0] for r in rows[:1]).lower()
        descriptions = category.get("descriptions") or []
        text = " ".join(
            str(d.get("text") or "") for d in descriptions if isinstance(d, dict)
        ).lower()
        combined = f"{label} {text}"
        if any(keyword in combined for keyword in _REVENUE_KEYWORDS):
            if rows:
                revenue = abs(rows[0][1])
                currency = currency or rows[0][2]
                break
    if revenue is None and categories:
        rows = walk_report_amounts(categories[0]) if isinstance(categories[0], dict) else []
        positive = [r for r in rows if r[1] > 0]
        if positive:
            revenue = positive[0][1]
            currency = currency or positive[0][2]
    return revenue, profit, currency


def period_from_statement(statement: dict) -> tuple[date | None, date | None]:
    period = statement.get("accountBalancePeriod") or statement.get("trialBalancePeriod") or {}
    if not isinstance(period, dict):
        return None, None
    return parse_date(period.get("startDate")), parse_date(period.get("endDate"))
