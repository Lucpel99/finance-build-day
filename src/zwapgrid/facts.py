from __future__ import annotations

from collections import Counter
from datetime import date, timedelta

from .client import ZwapgridClient, ZwapgridError
from .models import CashRow, IdentityFacts, MoneyFacts
from .parse import collect_payment_ids, parse_cash_row, parse_identity
from .remittance import MIN_SUBSTRING, normalize


def lookback_window(lookback_days: int = 365, *, today: date | None = None) -> tuple[date, date]:
    end = today or date.today()
    start = end - timedelta(days=lookback_days)
    return start, end


def fetch_identity(client: ZwapgridClient) -> IdentityFacts:
    return parse_identity(client.get_company_information())


def _needs_full_invoice(invoice: dict) -> bool:
    ref = str(invoice.get("reference") or "")
    ident = str(invoice.get("id") or "")
    folded_ref = normalize(ref).replace(" ", "")
    folded_id = normalize(ident).replace(" ", "")
    return len(folded_ref) < MIN_SUBSTRING and len(folded_id) < MIN_SUBSTRING


def _mark_unique_amounts(rows: list[CashRow]) -> None:
    keys = [
        (row.cash_amount, row.currency)
        for row in rows
        if row.cash_amount is not None and row.currency
    ]
    counts = Counter(keys)
    for row in rows:
        key = (row.cash_amount, row.currency)
        row.amount_unique_in_window = bool(
            row.cash_amount is not None and row.currency and counts.get(key, 0) == 1
        )


def _fetch_money(
    client: ZwapgridClient,
    *,
    direction: str,
    lookback_days: int = 365,
    today: date | None = None,
) -> MoneyFacts:
    window_start, window_end = lookback_window(lookback_days, today=today)
    start_s = window_start.isoformat()
    end_s = window_end.isoformat()

    if direction == "inbound":
        invoices, meta = client.iter_sales_invoices(
            from_invoice_date=start_s,
            to_invoice_date=end_s,
        )
        get_full = client.get_sales_invoice
        get_payments = client.iter_sales_invoice_payments_for_invoice
    else:
        invoices, meta = client.iter_supplier_invoices(
            from_invoice_date=start_s,
            to_invoice_date=end_s,
        )
        get_full = client.get_supplier_invoice
        get_payments = client.iter_supplier_invoice_payments_for_invoice

    rows: list[CashRow] = []
    for invoice in invoices:
        invoice_id = invoice.get("id")
        extra_needles: list[str] = []
        full = invoice
        if invoice_id and _needs_full_invoice(invoice):
            try:
                full = get_full(str(invoice_id))
                extra_needles.extend(collect_payment_ids(full))
            except ZwapgridError:
                full = invoice
        payments: list[dict] = []
        if invoice_id:
            try:
                payments, _ = get_payments(str(invoice_id))
            except ZwapgridError:
                payments = []
        rows.append(
            parse_cash_row(
                full,
                payments,
                direction=direction,
                extra_needles=extra_needles,
            )
        )

    _mark_unique_amounts(rows)
    return MoneyFacts(
        direction=direction,  # type: ignore[arg-type]
        window_start=window_start,
        window_end=window_end,
        total_resources=int(meta.get("totalResources") or len(rows)),
        pages_fetched=int(meta.get("pagesFetched") or 1),
        complete=bool(meta.get("complete", True)),
        rows=rows,
    )


def fetch_money_in(
    client: ZwapgridClient,
    *,
    lookback_days: int = 365,
    today: date | None = None,
) -> MoneyFacts:
    return _fetch_money(
        client, direction="inbound", lookback_days=lookback_days, today=today
    )


def fetch_money_out(
    client: ZwapgridClient,
    *,
    lookback_days: int = 365,
    today: date | None = None,
) -> MoneyFacts:
    return _fetch_money(
        client, direction="outbound", lookback_days=lookback_days, today=today
    )
