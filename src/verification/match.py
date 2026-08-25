from __future__ import annotations

from .models import BankTxEvent, BookCashEvent, BooksToBankReport, MatchOutcome


def _currency(value: str) -> str:
    return value.strip().upper()


def _days_apart(left: date, right: date) -> int:
    return abs((left - right).days)


def match_books_to_bank(
    books: list[BookCashEvent],
    bank_txs: list[BankTxEvent],
    *,
    grace_days: int = 5,
    flags: list[str] | None = None,
) -> BooksToBankReport:
    """One-to-one Z→B: paid invoices seek a booked bank tx.

    Gates: exact amount, exact currency, same direction, |cash_date − booking_date|
    ≤ grace_days. Unique-amount rows claim first. Closest date wins; a tie is
    ambiguous and does not consume the tx. Unmatched bank lines are ignored.
    """
    consumed: set[int] = set()
    ordered = sorted(
        enumerate(books),
        key=lambda item: (
            not item[1].amount_unique_in_window,
            item[1].cash_date,
            item[1].book_id or "",
        ),
    )

    outcomes_by_index: dict[int, MatchOutcome] = {}
    for book_index, book in ordered:
        book_ccy = _currency(book.currency)
        candidates: list[tuple[int, int]] = []
        for tx_index, tx in enumerate(bank_txs):
            if tx_index in consumed:
                continue
            if _currency(tx.currency) != book_ccy:
                continue
            if tx.amount != book.amount:
                continue
            if tx.direction != book.direction:
                continue
            gap = _days_apart(book.cash_date, tx.booking_date)
            if gap > grace_days:
                continue
            candidates.append((gap, tx_index))

        candidate_ids = [
            bank_txs[i].tx_id for _, i in candidates if bank_txs[i].tx_id
        ]
        base = dict(
            book_id=book.book_id,
            invoice_reference=book.invoice_reference,
            direction=book.direction,
            amount=book.amount,
            currency=book_ccy,
            cash_date=book.cash_date,
            candidate_tx_ids=candidate_ids,
        )
        if not candidates:
            outcomes_by_index[book_index] = MatchOutcome(status="unmatched", **base)
            continue

        best_gap = min(gap for gap, _ in candidates)
        closest = [i for gap, i in candidates if gap == best_gap]
        if len(closest) > 1:
            outcomes_by_index[book_index] = MatchOutcome(status="ambiguous", **base)
            continue

        tx_index = closest[0]
        consumed.add(tx_index)
        tx = bank_txs[tx_index]
        outcomes_by_index[book_index] = MatchOutcome(
            status="matched",
            tx_id=tx.tx_id,
            booking_date=tx.booking_date,
            days_apart=best_gap,
            **base,
        )

    outcomes = [outcomes_by_index[i] for i in range(len(books))]
    matched = sum(1 for item in outcomes if item.status == "matched")
    unmatched = sum(1 for item in outcomes if item.status == "unmatched")
    ambiguous = sum(1 for item in outcomes if item.status == "ambiguous")
    eligible = len(books)
    coverage = round(matched / eligible, 4) if eligible else None
    return BooksToBankReport(
        eligible=eligible,
        matched=matched,
        unmatched=unmatched,
        ambiguous=ambiguous,
        coverage=coverage,
        outcomes=outcomes,
        flags=list(dict.fromkeys(flags or [])),
    )
