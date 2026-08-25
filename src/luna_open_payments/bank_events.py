from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation

from .models import Transaction
from verification.models import BankTxEvent

_CREDIT = {"CRDT", "CREDIT", "CR", "C"}
_DEBIT = {"DBIT", "DEBIT", "DR", "D"}


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value).strip()[:10])
    except ValueError:
        return None


def _indicator_direction(raw: dict) -> str | None:
    indicator = raw.get("creditDebitIndicator") or raw.get("credit_debit_indicator")
    if not indicator:
        return None
    key = str(indicator).strip().upper()
    if key in _CREDIT:
        return "inbound"
    if key in _DEBIT:
        return "outbound"
    return None


def _signed_amount(tx: Transaction) -> Decimal | None:
    if not tx.transactionAmount or tx.transactionAmount.amount is None:
        return None
    try:
        return Decimal(str(tx.transactionAmount.amount))
    except (InvalidOperation, TypeError):
        return None


def as_bank_events(
    transactions: list[Transaction],
) -> tuple[list[BankTxEvent], list[str]]:
    """Project AIS transactions into SDK-free bank events.

    Direction prefers creditDebitIndicator. Signed amounts are used only when
    the batch contains a negative amount. Unsigned all-positive amounts with
    no indicator are skipped and flagged — they would otherwise all look inbound.
    """
    amounts = [_signed_amount(tx) for tx in transactions]
    signed_batch = any(amount is not None and amount < 0 for amount in amounts)

    events: list[BankTxEvent] = []
    skipped_unsigned = 0
    for tx, amount in zip(transactions, amounts):
        if amount is None:
            continue
        raw = tx.model_dump()
        direction = _indicator_direction(raw)
        if direction is None:
            if amount < 0:
                direction = "outbound"
            elif amount > 0 and signed_batch:
                direction = "inbound"
            else:
                skipped_unsigned += 1
                continue

        booking = _parse_date(tx.bookingDate) or _parse_date(tx.valueDate)
        if booking is None:
            continue
        currency = (tx.transactionAmount.currency if tx.transactionAmount else None) or ""
        if not currency:
            continue
        events.append(
            BankTxEvent(
                tx_id=tx.transactionId,
                direction=direction,  # type: ignore[arg-type]
                amount=abs(amount),
                currency=currency.upper(),
                booking_date=booking,
            )
        )

    flags: list[str] = []
    if skipped_unsigned:
        flags.append("unsigned_amount_no_indicator")
    return events, flags
