from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

Direction = Literal["inbound", "outbound"]
MatchStatus = Literal["matched", "ambiguous", "unmatched"]


class BookCashEvent(BaseModel):
    book_id: str | None = None
    invoice_reference: str | None = None
    direction: Direction
    amount: Decimal
    currency: str
    cash_date: date
    amount_unique_in_window: bool = False


class BankTxEvent(BaseModel):
    tx_id: str | None = None
    direction: Direction
    amount: Decimal
    currency: str
    booking_date: date


class MatchOutcome(BaseModel):
    book_id: str | None = None
    invoice_reference: str | None = None
    direction: Direction
    amount: Decimal
    currency: str
    cash_date: date
    status: MatchStatus
    tx_id: str | None = None
    booking_date: date | None = None
    days_apart: int | None = None
    candidate_tx_ids: list[str] = Field(default_factory=list)


class BooksToBankReport(BaseModel):
    eligible: int
    matched: int
    unmatched: int
    ambiguous: int
    coverage: float | None
    outcomes: list[MatchOutcome] = Field(default_factory=list)
    flags: list[str] = Field(default_factory=list)
