from __future__ import annotations

import math
from datetime import date
from decimal import Decimal

from .client import ZwapgridClient, ZwapgridError
from .models import (
    ClaimedOnboarding,
    ClaimReport,
    EdgeScore,
    Freshness,
    IdentityFacts,
    InvoiceSizeStats,
    MoneyFacts,
    RevenuePeriod,
    UnseenAccountSignals,
)
from .parse import extract_revenue, period_from_statement


def _shift_year(value: date, years: int) -> date:
    try:
        return value.replace(year=value.year + years)
    except ValueError:
        return value.replace(month=2, day=28, year=value.year + years)


def discover_fiscal_year(client: ZwapgridClient) -> tuple[date | None, date | None]:
    statement = client.get_income_statement()
    return period_from_statement(statement)


def fetch_revenue_series(
    client: ZwapgridClient,
    *,
    years: int = 3,
) -> list[RevenuePeriod]:
    current = client.get_income_statement()
    start, end = period_from_statement(current)
    periods: list[RevenuePeriod] = [_period_from(current, source="incomestatement_ytd")]

    if start and end:
        for offset in range(1, years):
            req_start = _shift_year(start, -offset)
            req_end = _shift_year(end, -offset)
            try:
                statement = client.get_income_statement(
                    start_date=req_start.isoformat(),
                    end_date=req_end.isoformat(),
                )
            except ZwapgridError:
                continue
            periods.append(_period_from(statement, source=f"incomestatement_fy-{offset}"))
    return periods


def _period_from(statement: dict, *, source: str) -> RevenuePeriod:
    start, end = period_from_statement(statement)
    days = (end - start).days + 1 if start and end else None
    revenue, profit, currency = extract_revenue(statement)
    annualized = None
    if revenue is not None and days and days > 0:
        annualized = (revenue * Decimal(365) / Decimal(days)).quantize(Decimal("0.01"))
    return RevenuePeriod(
        start=start,
        end=end,
        days=days,
        revenue=revenue,
        profit_loss=profit,
        annualized=annualized,
        currency=currency,
        source=source,
    )


def freshness(
    money_in: MoneyFacts | None,
    money_out: MoneyFacts | None = None,
    *,
    today: date | None = None,
) -> tuple[Freshness, date | None]:
    today = today or date.today()
    dates: list[date] = []
    for bundle in (money_in, money_out):
        if not bundle:
            continue
        for row in bundle.rows:
            for value in (row.cash_date, row.issue_date, row.settlement_date):
                if value:
                    dates.append(value)
    if not dates:
        return "dormant", None
    last = max(dates)
    age = (today - last).days
    if age <= 60:
        return "fresh", last
    if age <= 180:
        return "ageing", last
    return "stale", last


def _percentile(sorted_vals: list[Decimal], pct: float) -> Decimal:
    if not sorted_vals:
        raise ValueError("empty")
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    rank = (len(sorted_vals) - 1) * pct
    lo = math.floor(rank)
    hi = math.ceil(rank)
    if lo == hi:
        return sorted_vals[lo]
    weight = Decimal(str(rank - lo))
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * weight


def invoice_size_stats(money: MoneyFacts) -> list[InvoiceSizeStats]:
    by_ccy: dict[str, list[Decimal]] = {}
    for row in money.rows:
        if row.cancelled or row.credit_note:
            continue
        amount = row.tax_inclusive or row.cash_amount
        if amount is None or not row.currency:
            continue
        by_ccy.setdefault(row.currency, []).append(amount)

    stats: list[InvoiceSizeStats] = []
    for currency, values in by_ccy.items():
        ordered = sorted(values)
        total = sum(ordered, Decimal("0"))
        n = len(ordered)
        stats.append(
            InvoiceSizeStats(
                currency=currency,
                count=n,
                total=total,
                mean=(total / n).quantize(Decimal("0.01")) if n else None,
                median=_percentile(ordered, 0.5),
                p90=_percentile(ordered, 0.9),
                p95=_percentile(ordered, 0.95),
                max=ordered[-1],
            )
        )
    stats.sort(key=lambda item: item.count, reverse=True)
    return stats


def agreement_from_ratio(ratio: float | None) -> float | None:
    if ratio is None or ratio <= 0:
        return None
    log_dist = abs(math.log(ratio))
    return max(0.0, min(1.0, 1.0 - log_dist / math.log(2.5)))


def _confidence(*, days: int | None, count: int, freshness_tier: Freshness) -> float:
    if freshness_tier == "dormant":
        return 0.0
    day_score = 0.0 if not days else min(1.0, days / 365)
    count_score = min(1.0, count / 30)
    base = 0.5 * day_score + 0.5 * count_score
    if freshness_tier == "stale":
        base = min(base, 0.25)
    elif freshness_tier == "ageing":
        base *= 0.7
    if days is not None and days < 90:
        base = min(base, 0.2)
    return round(base, 3)


def _pick_revenue_basis(
    periods: list[RevenuePeriod],
    *,
    today: date,
) -> tuple[Decimal | None, str, int | None, list[str]]:
    flags: list[str] = []
    closed = [
        p
        for p in periods
        if p.revenue is not None
        and p.end
        and p.days
        and p.days >= 300
        and p.end <= today
    ]
    closed.sort(key=lambda p: p.end or date.min, reverse=True)
    if closed:
        chosen = closed[0]
        age = (today - chosen.end).days if chosen.end else None
        extra: list[str] = []
        if age and age > 180:
            extra.append("stale_books")
        return chosen.revenue, chosen.source, chosen.days, extra

    ytd = next((p for p in periods if p.source == "incomestatement_ytd"), periods[0] if periods else None)
    if not ytd or ytd.revenue is None:
        return None, "none", None, ["insufficient_history"]
    if not ytd.days or ytd.days < 90:
        flags.append("insufficient_history")
        return ytd.revenue, ytd.source, ytd.days, flags
    if ytd.annualized is None:
        return ytd.revenue, ytd.source, ytd.days, flags
    return ytd.annualized, f"{ytd.source}_annualized", ytd.days, flags


def score_claims(
    claimed: ClaimedOnboarding,
    *,
    periods: list[RevenuePeriod],
    stats: list[InvoiceSizeStats],
    freshness_tier: Freshness,
    today: date | None = None,
) -> list[EdgeScore]:
    today = today or date.today()
    scores: list[EdgeScore] = []
    observed, basis, days, flags = _pick_revenue_basis(periods, today=today)
    n = sum(s.count for s in stats)
    if n < 5:
        flags.append("insufficient_history")
    flags = list(dict.fromkeys(flags))
    confidence = _confidence(days=days, count=n, freshness_tier=freshness_tier)
    if n < 5:
        confidence = min(confidence, 0.2)
    if freshness_tier == "stale" and "stale_books" not in flags:
        flags.append("stale_books")

    ratio = None
    if claimed.yearly_revenue and observed and observed != 0:
        ratio = float(claimed.yearly_revenue / observed)
    scores.append(
        EdgeScore(
            metric="yearly_revenue",
            claimed=claimed.yearly_revenue,
            observed=observed,
            basis=basis,
            ratio=ratio,
            agreement=agreement_from_ratio(ratio),
            confidence=confidence,
            freshness=freshness_tier,
            flags=list(flags),
        )
    )

    primary = stats[0] if stats else None
    if primary:
        avg_ratio = None
        avg_flags: list[str] = []
        if claimed.average_transaction and primary.median and primary.median != 0:
            avg_ratio = float(claimed.average_transaction / primary.median)
        if (
            claimed.yearly_revenue
            and claimed.average_transaction
            and claimed.average_transaction != 0
        ):
            implied = claimed.yearly_revenue / claimed.average_transaction
            if primary.count and (
                implied / Decimal(primary.count) > 10
                or Decimal(primary.count) / implied > 10
            ):
                avg_flags.append("implied_count_mismatch")
        scores.append(
            EdgeScore(
                metric="average_transaction",
                claimed=claimed.average_transaction,
                observed=primary.median,
                basis=f"invoice_median_{primary.currency}_n={primary.count}",
                ratio=avg_ratio,
                agreement=agreement_from_ratio(avg_ratio),
                confidence=_confidence(
                    days=365, count=primary.count, freshness_tier=freshness_tier
                ),
                freshness=freshness_tier,
                flags=avg_flags,
            )
        )

        max_flags: list[str] = []
        max_ratio = None
        if claimed.max_transaction and primary.max and primary.max != 0:
            max_ratio = float(claimed.max_transaction / primary.max)
            if primary.max > claimed.max_transaction * Decimal("1.5"):
                max_flags.append("understated_exposure")
            if (
                claimed.max_transaction > primary.max * Decimal("3")
                and primary.count >= 30
            ):
                max_flags.append("overstated")
        scores.append(
            EdgeScore(
                metric="max_transaction",
                claimed=claimed.max_transaction,
                observed=primary.max,
                basis=f"invoice_max_{primary.currency}_n={primary.count}",
                ratio=max_ratio,
                agreement=agreement_from_ratio(max_ratio),
                confidence=_confidence(
                    days=365, count=primary.count, freshness_tier=freshness_tier
                ),
                freshness=freshness_tier,
                flags=max_flags,
            )
        )
    return scores


def unseen_account_signals(
    identity: IdentityFacts,
    *money: MoneyFacts,
    connected_account_ids: list[str] | None = None,
) -> UnseenAccountSignals:
    ledger: list[str] = []
    seen_ledger: set[str] = set()
    for bundle in money:
        for row in bundle.rows:
            if not row.paid:
                continue
            for payment in row.payments:
                ref = payment.ledger_account_ref
                if ref and ref not in seen_ledger:
                    seen_ledger.add(ref)
                    ledger.append(ref)

    notes: list[str] = []
    if len(ledger) > 1:
        notes.append(
            f"Books post cash to {len(ledger)} ledger bank accounts; "
            "confirm each is among the connected AIS accounts."
        )

    connected = {
        item.replace(" ", "").replace("-", "").upper()
        for item in (connected_account_ids or [])
        if item
    }
    unnamed = []
    for account in identity.bank_accounts:
        if account.usable and connected and account.normalized not in connected:
            unnamed.append(account.raw_id)
    if unnamed:
        notes.append(
            "Company paymentMeans name account(s) not in the connected AIS set."
        )
    if identity.bank_accounts_unusable:
        notes.append("Zwapgrid paymentMeans ids do not look like IBAN/BBAN.")

    return UnseenAccountSignals(
        ledger_bank_accounts=ledger,
        payment_means_ids=[a.raw_id for a in identity.bank_accounts],
        notes=notes,
    )


def build_claim_report(
    client: ZwapgridClient,
    claimed: ClaimedOnboarding,
    money_in: MoneyFacts,
    money_out: MoneyFacts | None = None,
    identity: IdentityFacts | None = None,
    *,
    connected_account_ids: list[str] | None = None,
    today: date | None = None,
) -> ClaimReport:
    today = today or date.today()
    periods = fetch_revenue_series(client)
    stats = invoice_size_stats(money_in)
    tier, last = freshness(money_in, money_out, today=today)
    scores = score_claims(
        claimed,
        periods=periods,
        stats=stats,
        freshness_tier=tier,
        today=today,
    )
    identity = identity or IdentityFacts()
    unseen = unseen_account_signals(
        identity,
        money_in,
        *( [money_out] if money_out else [] ),
        connected_account_ids=connected_account_ids,
    )
    dominant = stats[0] if stats else None
    return ClaimReport(
        freshness=tier,
        last_activity=last,
        revenue_periods=periods,
        invoice_stats=stats,
        invoice_revenue=dominant.total if dominant else None,
        invoice_revenue_currency=dominant.currency if dominant else None,
        claim_vs_books=scores,
        unseen_accounts=unseen,
    )
