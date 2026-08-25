from __future__ import annotations

from .models import CashRow, MoneyFacts
from verification.models import BookCashEvent


def _row_to_event(row: CashRow) -> BookCashEvent | None:
    if not row.match_eligible:
        return None
    if row.cash_amount is None or not row.currency or row.cash_date is None:
        return None
    return BookCashEvent(
        book_id=row.invoice_id,
        invoice_reference=row.invoice_reference,
        direction=row.direction,
        amount=row.cash_amount,
        currency=row.currency.upper(),
        cash_date=row.cash_date,
        amount_unique_in_window=row.amount_unique_in_window,
    )


def as_book_events(*money: MoneyFacts | None) -> list[BookCashEvent]:
    """Project paid invoice cash rows into SDK-free book events for Z→B matching."""
    events: list[BookCashEvent] = []
    for bundle in money:
        if bundle is None:
            continue
        for row in bundle.rows:
            event = _row_to_event(row)
            if event is not None:
                events.append(event)
    return events
