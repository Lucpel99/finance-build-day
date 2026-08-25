from datetime import date
from decimal import Decimal

from zwapgrid.claims import (
    agreement_from_ratio,
    freshness,
    invoice_size_stats,
    score_claims,
    unseen_account_signals,
)
from zwapgrid.models import (
    BankAccountFact,
    CashRow,
    ClaimedOnboarding,
    IdentityFacts,
    MoneyFacts,
    PaymentFact,
    RevenuePeriod,
)
from zwapgrid.parse import parse_cash_row
import json
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"


def _money(rows: list[CashRow], *, direction="inbound") -> MoneyFacts:
    return MoneyFacts(
        direction=direction,
        window_start=date(2025, 8, 25),
        window_end=date(2026, 8, 25),
        total_resources=len(rows),
        pages_fetched=1,
        complete=True,
        rows=rows,
    )


def test_freshness_fresh_vs_dormant():
    invoice = json.loads((FIXTURES / "money_in/sales_invoice_seed.json").read_text())
    row = parse_cash_row(invoice, [], direction="inbound")
    tier, last = freshness(_money([row]), today=date(2026, 8, 25))
    assert tier == "fresh"
    assert last == date(2026, 8, 25)
    empty = _money([])
    assert freshness(empty, today=date(2026, 8, 25))[0] == "dormant"


def test_invoice_size_stats_median_not_skewed_by_outlier():
    rows = [
        CashRow(
            direction="inbound",
            tax_inclusive=Decimal(n),
            currency="SEK",
        )
        for n in (100, 110, 120, 130, 10000)
    ]
    stats = invoice_size_stats(_money(rows))
    assert stats[0].median == Decimal("120")
    assert stats[0].max == Decimal("10000")
    assert stats[0].count == 5


def test_score_claims_insufficient_history_on_short_ytd():
    claimed = ClaimedOnboarding(
        yearly_revenue=Decimal("1000000"),
        average_transaction=Decimal("3000"),
        max_transaction=Decimal("5000"),
    )
    periods = [
        RevenuePeriod(
            start=date(2026, 8, 1),
            end=date(2026, 8, 25),
            days=25,
            revenue=Decimal("3281"),
            annualized=Decimal("3281") * Decimal(365) / Decimal(25),
            currency="SEK",
            source="incomestatement_ytd",
        )
    ]
    invoice = json.loads((FIXTURES / "money_in/sales_invoice_seed.json").read_text())
    stats = invoice_size_stats(_money([parse_cash_row(invoice, [], direction="inbound")]))
    scores = score_claims(
        claimed,
        periods=periods,
        stats=stats,
        freshness_tier="fresh",
        today=date(2026, 8, 25),
    )
    revenue = next(s for s in scores if s.metric == "yearly_revenue")
    assert "insufficient_history" in revenue.flags
    assert revenue.confidence <= 0.2


def test_agreement_and_implied_count_flag():
    assert agreement_from_ratio(1.0) == 1.0
    assert agreement_from_ratio(2.5) == 0.0
    claimed = ClaimedOnboarding(
        yearly_revenue=Decimal("10000000"),
        average_transaction=Decimal("10"),
        max_transaction=Decimal("50"),
    )
    periods = [
        RevenuePeriod(
            start=date(2025, 1, 1),
            end=date(2025, 12, 31),
            days=365,
            revenue=Decimal("10000000"),
            currency="SEK",
            source="incomestatement_fy-1",
        )
    ]
    rows = [
        CashRow(direction="inbound", tax_inclusive=Decimal("100"), currency="SEK")
        for _ in range(5)
    ]
    scores = score_claims(
        claimed,
        periods=periods,
        stats=invoice_size_stats(_money(rows)),
        freshness_tier="fresh",
        today=date(2026, 8, 25),
    )
    avg = next(s for s in scores if s.metric == "average_transaction")
    assert "implied_count_mismatch" in avg.flags
    rev = next(s for s in scores if s.metric == "yearly_revenue")
    assert rev.agreement == 1.0
    assert rev.basis == "incomestatement_fy-1"


def test_unseen_account_signals():
    identity = IdentityFacts(
        bank_accounts=[
            BankAccountFact(
                raw_id="SE4550000000058398257466",
                normalized="SE4550000000058398257466",
                usable=True,
            )
        ]
    )
    row = CashRow(
        direction="inbound",
        paid=True,
        payments=[PaymentFact(ledger_account_ref="5233")],
    )
    signals = unseen_account_signals(
        identity,
        _money([row]),
        connected_account_ids=["NL00BANK0123456789"],
    )
    assert "5233" in signals.ledger_bank_accounts
    assert any("not in the connected AIS set" in note for note in signals.notes)
