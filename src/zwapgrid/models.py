from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

Direction = Literal["inbound", "outbound"]
Freshness = Literal["fresh", "ageing", "stale", "dormant"]


class Identifier(BaseModel):
    id: str | None = None
    scheme_id: str | None = None


class AddressFacts(BaseModel):
    street: str | None = None
    building: str | None = None
    postal_code: str | None = None
    city: str | None = None
    country_code: str | None = None


class BankAccountFact(BaseModel):
    raw_id: str
    normalized: str
    institution: str | None = None
    usable: bool = False


class IdentityFacts(BaseModel):
    legal_name: str | None = None
    trading_name: str | None = None
    organization_number: Identifier | None = None
    other_identifiers: list[Identifier] = Field(default_factory=list)
    address: AddressFacts | None = None
    phone: str | None = None
    email: str | None = None
    bank_accounts: list[BankAccountFact] = Field(default_factory=list)
    bank_accounts_unusable: bool = False


class PaymentFact(BaseModel):
    id: str | None = None
    reference: str | None = None
    amount: Decimal | None = None
    currency: str | None = None
    paid_date: date | None = None
    received_date: date | None = None
    booked_date: date | None = None
    booked: bool | None = None
    billing_invoice_ids: list[str] = Field(default_factory=list)
    ledger_account_ref: str | None = None
    ledger_account_name: str | None = None


class CashRow(BaseModel):
    direction: Direction
    invoice_id: str | None = None
    invoice_reference: str | None = None
    counterparty: str | None = None
    normalized_counterparty: str | None = None
    issue_date: date | None = None
    due_date: date | None = None
    settlement_date: date | None = None
    status: str | None = None
    paid: bool = False
    cancelled: bool = False
    credit_note: bool = False
    tax_inclusive: Decimal | None = None
    remaining: Decimal | None = None
    currency: str | None = None
    cash_amount: Decimal | None = None
    cash_date: date | None = None
    cash_date_source: str | None = None
    remittance_needles: list[str] = Field(default_factory=list)
    amount_unique_in_window: bool = False
    payments: list[PaymentFact] = Field(default_factory=list)
    match_eligible: bool = False


class MoneyFacts(BaseModel):
    direction: Direction
    window_start: date
    window_end: date
    total_resources: int
    pages_fetched: int
    complete: bool
    rows: list[CashRow] = Field(default_factory=list)


class RevenuePeriod(BaseModel):
    start: date | None = None
    end: date | None = None
    days: int | None = None
    revenue: Decimal | None = None
    profit_loss: Decimal | None = None
    annualized: Decimal | None = None
    currency: str | None = None
    source: str = "incomestatement"


class InvoiceSizeStats(BaseModel):
    currency: str
    count: int = 0
    total: Decimal = Decimal("0")
    mean: Decimal | None = None
    median: Decimal | None = None
    p90: Decimal | None = None
    p95: Decimal | None = None
    max: Decimal | None = None


class ClaimedOnboarding(BaseModel):
    yearly_revenue: Decimal | None = None
    average_transaction: Decimal | None = None
    max_transaction: Decimal | None = None
    currency: str | None = None


class EdgeScore(BaseModel):
    metric: str
    claimed: Decimal | None = None
    observed: Decimal | None = None
    basis: str
    ratio: float | None = None
    agreement: float | None = None
    confidence: float
    freshness: Freshness
    flags: list[str] = Field(default_factory=list)


class UnseenAccountSignals(BaseModel):
    ledger_bank_accounts: list[str] = Field(default_factory=list)
    payment_means_ids: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class ClaimReport(BaseModel):
    freshness: Freshness
    last_activity: date | None = None
    revenue_periods: list[RevenuePeriod] = Field(default_factory=list)
    invoice_stats: list[InvoiceSizeStats] = Field(default_factory=list)
    invoice_revenue: Decimal | None = None
    invoice_revenue_currency: str | None = None
    claim_vs_books: list[EdgeScore] = Field(default_factory=list)
    unseen_accounts: UnseenAccountSignals = Field(default_factory=UnseenAccountSignals)
