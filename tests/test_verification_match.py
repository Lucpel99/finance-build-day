from datetime import date
from decimal import Decimal
from pathlib import Path
import json

from luna_open_payments.bank_events import as_bank_events
from luna_open_payments.models import Transaction
from verification import BankTxEvent, BookCashEvent, match_books_to_bank
from zwapgrid import as_book_events
from zwapgrid.models import MoneyFacts
from zwapgrid.parse import parse_cash_row

FIXTURES = Path(__file__).parent / "fixtures"


def _money(rows, *, direction="inbound") -> MoneyFacts:
    return MoneyFacts(
        direction=direction,
        window_start=date(2025, 8, 25),
        window_end=date(2026, 8, 25),
        total_resources=len(rows),
        pages_fetched=1,
        complete=True,
        rows=rows,
    )


def _book(**kwargs) -> BookCashEvent:
    defaults = dict(
        book_id="inv-1",
        invoice_reference="INV-1",
        direction="inbound",
        amount=Decimal("3281.25"),
        currency="SEK",
        cash_date=date(2026, 8, 25),
        amount_unique_in_window=True,
    )
    defaults.update(kwargs)
    return BookCashEvent(**defaults)


def _tx(**kwargs) -> BankTxEvent:
    defaults = dict(
        tx_id="tx-1",
        direction="inbound",
        amount=Decimal("3281.25"),
        currency="SEK",
        booking_date=date(2026, 8, 25),
    )
    defaults.update(kwargs)
    return BankTxEvent(**defaults)


def test_unique_amount_within_grace_matches():
    report = match_books_to_bank(
        [_book(cash_date=date(2026, 8, 25))],
        [_tx(booking_date=date(2026, 8, 28))],
    )
    assert report.matched == 1
    assert report.unmatched == 0
    assert report.coverage == 1.0
    assert report.outcomes[0].status == "matched"
    assert report.outcomes[0].tx_id == "tx-1"
    assert report.outcomes[0].days_apart == 3


def test_date_outside_grace_is_unmatched():
    report = match_books_to_bank(
        [_book(cash_date=date(2026, 8, 25))],
        [_tx(booking_date=date(2026, 8, 31))],
    )
    assert report.outcomes[0].status == "unmatched"
    assert report.matched == 0


def test_wrong_direction_is_unmatched():
    report = match_books_to_bank(
        [_book(direction="inbound")],
        [_tx(direction="outbound")],
    )
    assert report.outcomes[0].status == "unmatched"


def test_consumed_tx_not_reused():
    books = [
        _book(book_id="a", amount_unique_in_window=True),
        _book(book_id="b", amount_unique_in_window=True),
    ]
    report = match_books_to_bank(books, [_tx()])
    statuses = {item.book_id: item.status for item in report.outcomes}
    assert statuses["a"] == "matched"
    assert statuses["b"] == "unmatched"
    assert report.matched == 1
    assert report.unmatched == 1


def test_closest_date_wins_when_unique():
    report = match_books_to_bank(
        [_book()],
        [
            _tx(tx_id="far", booking_date=date(2026, 8, 30)),
            _tx(tx_id="near", booking_date=date(2026, 8, 26)),
        ],
    )
    assert report.outcomes[0].status == "matched"
    assert report.outcomes[0].tx_id == "near"


def test_tied_closest_date_is_ambiguous_and_does_not_consume():
    books = [
        _book(book_id="first"),
        _book(book_id="second"),
    ]
    txs = [
        _tx(tx_id="left", booking_date=date(2026, 8, 24)),
        _tx(tx_id="right", booking_date=date(2026, 8, 26)),
    ]
    report = match_books_to_bank(books, txs)
    assert all(item.status == "ambiguous" for item in report.outcomes)
    assert report.ambiguous == 2
    assert report.matched == 0


def test_currency_and_amount_must_be_exact():
    report = match_books_to_bank(
        [_book(amount=Decimal("3281.25"), currency="SEK")],
        [_tx(amount=Decimal("3281.00"), currency="SEK")],
    )
    assert report.outcomes[0].status == "unmatched"
    report = match_books_to_bank(
        [_book(currency="SEK")],
        [_tx(currency="DKK")],
    )
    assert report.outcomes[0].status == "unmatched"


def test_seed_invoices_vs_ais_fixture_are_unmatched():
    sales = parse_cash_row(
        json.loads((FIXTURES / "money_in/sales_invoice_seed.json").read_text()),
        [],
        direction="inbound",
    )
    supplier = parse_cash_row(
        json.loads((FIXTURES / "money_out/supplier_seed.json").read_text()),
        [],
        direction="outbound",
    )
    books = as_book_events(_money([sales]), _money([supplier], direction="outbound"))
    assert len(books) == 2

    fixture = Transaction.model_validate(
        json.loads((FIXTURES / "money_in/ais_transaction.json").read_text())
    )
    credited = Transaction.model_validate(
        {**fixture.model_dump(), "creditDebitIndicator": "CRDT"}
    )
    bank, flags = as_bank_events([credited])
    assert bank and not flags

    live_shaped = [
        _book(
            book_id="1",
            invoice_reference="1",
            direction="inbound",
            amount=Decimal("3281.25"),
            currency="SEK",
            cash_date=date(2026, 8, 25),
        ),
        _book(
            book_id="SUP-01",
            invoice_reference="ZG-SEED-c074a1dd2f09495e81a08e428800344e-SUP-01",
            direction="outbound",
            amount=Decimal("2687.50"),
            currency="SEK",
            cash_date=date(2026, 8, 25),
        ),
    ]
    report = match_books_to_bank(live_shaped, bank)
    assert report.eligible == 2
    assert report.matched == 0
    assert report.unmatched == 2
    assert report.coverage == 0.0

    seed_report = match_books_to_bank(books, bank)
    assert seed_report.matched == 0
    assert seed_report.eligible == 2


def test_as_bank_events_skips_unsigned_all_positive():
    fixture = Transaction.model_validate(
        json.loads((FIXTURES / "money_in/ais_transaction.json").read_text())
    )
    events, flags = as_bank_events([fixture])
    assert events == []
    assert "unsigned_amount_no_indicator" in flags


def test_as_bank_events_uses_indicator_then_signed_amount():
    credit = Transaction.model_validate(
        {
            "transactionId": "c1",
            "bookingDate": "2026-08-25",
            "transactionAmount": {"currency": "SEK", "amount": "3281.25"},
            "creditDebitIndicator": "CRDT",
        }
    )
    debit = Transaction.model_validate(
        {
            "transactionId": "d1",
            "valueDate": "2026-08-25",
            "transactionAmount": {"currency": "SEK", "amount": "-2687.50"},
        }
    )
    events, flags = as_bank_events([credit, debit])
    assert flags == []
    by_id = {item.tx_id: item for item in events}
    assert by_id["c1"].direction == "inbound"
    assert by_id["c1"].amount == Decimal("3281.25")
    assert by_id["d1"].direction == "outbound"
    assert by_id["d1"].amount == Decimal("2687.50")
    assert by_id["d1"].booking_date == date(2026, 8, 25)


def test_as_book_events_drops_unpaid_and_incomplete():
    unpaid = parse_cash_row(
        json.loads((FIXTURES / "money_in/sales_invoice_unpaid.json").read_text()),
        [],
        direction="inbound",
    )
    paid = parse_cash_row(
        json.loads((FIXTURES / "money_in/sales_invoice_seed.json").read_text()),
        [],
        direction="inbound",
    )
    events = as_book_events(_money([unpaid, paid]))
    assert len(events) == 1
    assert events[0].amount == Decimal("3281.00")
    assert events[0].cash_date == date(2026, 8, 25)
