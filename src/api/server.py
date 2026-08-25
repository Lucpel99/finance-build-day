# Run with: uvicorn src.api.server:app --reload --port 8000
from __future__ import annotations

import os
import random
from datetime import date, timedelta
from decimal import Decimal

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()

app = FastAPI(title="Luna Verification API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
    ],
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


# ── Request / Response models ─────────────────────────────────

class ClaimedValues(BaseModel):
    yearly_revenue: float
    avg_transaction: float
    max_transaction: float


class ComparisonRow(BaseModel):
    id: str
    label: str
    status: str
    statusLabel: str
    userInput: str
    openBanking: str
    accounting: str


class VerifyResponse(BaseModel):
    comparison: list[ComparisonRow]


# ── Helpers ───────────────────────────────────────────────────

def _fmt(val: float | None) -> str:
    if val is None:
        return "N/A"
    return f"{int(round(val)):,}".replace(",", " ") + " SEK"


def _determine_status(
    user_val: float,
    banking_val: float | None,
    accounting_val: float | None,
) -> tuple[str, str]:
    devs: list[float] = []
    if banking_val and user_val:
        devs.append(abs(user_val - banking_val) / user_val * 100)
    if accounting_val and user_val:
        devs.append(abs(user_val - accounting_val) / user_val * 100)
    max_dev = max(devs) if devs else 0
    if max_dev < 5:
        return "match", "Exact match"
    if max_dev < 20:
        return "close_match", "Close match"
    return "mismatch", "Needs review"


def _mock_banking(val: float, seed: int) -> float:
    rng = random.Random(seed)
    return round(val * rng.uniform(0.88, 1.12))


def _mock_accounting(val: float, seed: int) -> float:
    rng = random.Random(seed + 1000)
    return round(val * rng.uniform(0.90, 1.10))


# ── OpenPayments fetch ────────────────────────────────────────

def _fetch_banking(claimed: ClaimedValues) -> dict[str, float | None]:
    client_id = os.getenv("OPEN_PAYMENTS_CLIENT_ID")
    client_secret = os.getenv("OPEN_PAYMENTS_CLIENT_SECRET")
    bic = os.getenv("OPEN_PAYMENTS_BIC")
    psu_id = os.getenv("OPEN_PAYMENTS_PSU_ID")
    consent_id = os.getenv("OPEN_PAYMENTS_CONSENT_ID")
    env = os.getenv("OPEN_PAYMENTS_ENV", "sandbox")

    if not all([client_id, client_secret, bic, psu_id, consent_id]):
        # Fall back to derived mock when credentials are incomplete
        seed = int(claimed.yearly_revenue) % 999983
        return {
            "yearly_revenue": _mock_banking(claimed.yearly_revenue, seed),
            "avg_transaction": _mock_banking(claimed.avg_transaction, seed + 1),
            "max_transaction": _mock_banking(claimed.max_transaction, seed + 2),
        }

    try:
        from luna_open_payments.auth import TokenClient
        from luna_open_payments.client import OpenPaymentsClient
        from luna_open_payments.ais import AisService
        from luna_open_payments.bank_verification import calculate_transaction_metrics

        token_client = TokenClient(client_id, client_secret, env=env)
        client = OpenPaymentsClient(token_client, env=env)
        ais = AisService(client)

        accounts = ais.list_accounts(consent_id, bic, psu_id)
        if not accounts:
            raise ValueError("No accounts returned")

        account_id = accounts[0].resourceId
        date_from = (date.today() - timedelta(days=365)).isoformat()
        txs = ais.get_transactions(
            account_id=account_id,
            consent_id=consent_id,
            bic_fi=bic,
            psu_id=psu_id,
            date_from=date_from,
            booking_status="booked",
        )

        metrics = calculate_transaction_metrics(txs)

        incoming_amounts = [
            Decimal(t.transactionAmount.amount)
            for t in txs
            if t.transactionAmount
            and Decimal(t.transactionAmount.amount) > 0
        ]
        max_incoming = float(max(incoming_amounts)) if incoming_amounts else None

        return {
            "yearly_revenue": metrics["incoming_total"],
            "avg_transaction": metrics["average_incoming_transaction"],
            "max_transaction": max_incoming,
        }
    except Exception as exc:
        print(f"[OpenPayments] fetch failed, using mock: {exc}")
        seed = int(claimed.yearly_revenue) % 999983
        return {
            "yearly_revenue": _mock_banking(claimed.yearly_revenue, seed),
            "avg_transaction": _mock_banking(claimed.avg_transaction, seed + 1),
            "max_transaction": _mock_banking(claimed.max_transaction, seed + 2),
        }


# ── Zwapgrid fetch ────────────────────────────────────────────

def _fetch_accounting(claimed: ClaimedValues) -> dict[str, float | None]:
    api_key = os.getenv("ZWAPGRID_API_KEY")
    if not api_key:
        seed = int(claimed.yearly_revenue) % 999983
        return {
            "yearly_revenue": _mock_accounting(claimed.yearly_revenue, seed),
            "avg_transaction": _mock_accounting(claimed.avg_transaction, seed + 1),
            "max_transaction": _mock_accounting(claimed.max_transaction, seed + 2),
        }

    try:
        from zwapgrid import ZwapgridClient
        from zwapgrid.claims import build_claim_report
        from zwapgrid.facts import fetch_money_in
        from zwapgrid.models import ClaimedOnboarding

        zw = ZwapgridClient.from_env()
        onboarding = ClaimedOnboarding(
            yearly_revenue=Decimal(str(claimed.yearly_revenue)),
            average_transaction=Decimal(str(claimed.avg_transaction)),
            max_transaction=Decimal(str(claimed.max_transaction)),
        )
        money_in = fetch_money_in(zw, lookback_days=365)
        report = build_claim_report(zw, onboarding, money_in)

        result: dict[str, float | None] = {}
        for score in report.claim_vs_books:
            if score.observed is not None:
                # score.metric is "yearly_revenue", "average_transaction", "max_transaction"
                key = score.metric.replace("average_transaction", "avg_transaction")
                result[key] = float(score.observed)
        return result
    except Exception as exc:
        print(f"[Zwapgrid] fetch failed, using mock: {exc}")
        seed = int(claimed.yearly_revenue) % 999983
        return {
            "yearly_revenue": _mock_accounting(claimed.yearly_revenue, seed),
            "avg_transaction": _mock_accounting(claimed.avg_transaction, seed + 1),
            "max_transaction": _mock_accounting(claimed.max_transaction, seed + 2),
        }


# ── Endpoint ──────────────────────────────────────────────────

@app.post("/api/verify", response_model=VerifyResponse)
def verify(body: ClaimedValues) -> VerifyResponse:
    banking = _fetch_banking(body)
    accounting = _fetch_accounting(body)

    fields = [
        ("yearly_revenue",  "Estimated yearly revenue",  body.yearly_revenue),
        ("avg_transaction", "Avg. transaction value",    body.avg_transaction),
        ("max_transaction", "Max. transaction value",    body.max_transaction),
    ]

    rows: list[ComparisonRow] = []
    for field_id, label, user_val in fields:
        b_val = banking.get(field_id)
        a_val = accounting.get(field_id)
        status, status_label = _determine_status(user_val, b_val, a_val)
        rows.append(ComparisonRow(
            id=field_id,
            label=label,
            status=status,
            statusLabel=status_label,
            userInput=_fmt(user_val),
            openBanking=_fmt(b_val),
            accounting=_fmt(a_val),
        ))

    return VerifyResponse(comparison=rows)


# ── /api/match ────────────────────────────────────────────────

_MOCK_BANK_TXS = [
    {"tx_id": "TX-001", "date": "2026-05-12", "counterparty": "Bear Brothers AB",      "description": "Coffee - Colombia",        "amount": 28500, "currency": "SEK", "direction": "inbound"},
    {"tx_id": "TX-002", "date": "2026-05-10", "counterparty": "H&M AB",                "description": "Milk delivery - Week 11",   "amount":  4225, "currency": "SEK", "direction": "inbound"},
    {"tx_id": "TX-003", "date": "2026-05-09", "counterparty": "Cash & Carry Group AB", "description": "Paper cups & lids",         "amount":  3215, "currency": "SEK", "direction": "inbound"},
    {"tx_id": "TX-004", "date": "2026-05-08", "counterparty": "Ikea Card Services",    "description": "Card kickback #507",        "amount": 17100, "currency": "SEK", "direction": "inbound"},
    {"tx_id": "TX-005", "date": "2026-05-06", "counterparty": "Roast House Sweden",    "description": "Espresso blend - 5kg",      "amount":  4680, "currency": "SEK", "direction": "inbound"},
    {"tx_id": "TX-006", "date": "2026-05-04", "counterparty": "Packaging Partner AB",  "description": "Takeaway bags",             "amount":  2560, "currency": "SEK", "direction": "inbound"},
]

_MOCK_INVOICES = [
    {"book_id": "INV-3487", "invoice_reference": "INV-3487", "date": "2026-05-12", "counterparty": "Bear Brothers AB",      "amount": 30565, "currency": "SEK", "direction": "inbound"},
    {"book_id": "INV-2136", "invoice_reference": "INV-2136", "date": "2026-05-11", "counterparty": "H&M AB",                "amount":  6450, "currency": "SEK", "direction": "inbound"},
    {"book_id": "INV-3214", "invoice_reference": "INV-3214", "date": "2026-05-10", "counterparty": "Cash & Carry Group AB", "amount":  5590, "currency": "SEK", "direction": "inbound"},
    {"book_id": "INV-990",  "invoice_reference": "INV-990",  "date": "2026-05-08", "counterparty": "Ikea Card Services",   "amount": 18000, "currency": "SEK", "direction": "inbound"},
    {"book_id": "INV-7542", "invoice_reference": "INV-7542", "date": "2026-05-07", "counterparty": "Roast House Sweden",   "amount":  6170, "currency": "SEK", "direction": "inbound"},
    {"book_id": "INV-4655", "invoice_reference": "INV-4655", "date": "2026-05-05", "counterparty": "Packaging Partner AB", "amount":  2250, "currency": "SEK", "direction": "inbound"},
]


def _fetch_match_data() -> tuple[list[dict], list[dict]]:
    """Return (bank_transactions, invoices) as display dicts, with real data where available."""
    from decimal import Decimal as D

    bank_rows: list[dict] = []
    invoice_rows: list[dict] = []

    # ── OpenPayments → bank transactions ──────────────────────
    client_id     = os.getenv("OPEN_PAYMENTS_CLIENT_ID")
    client_secret = os.getenv("OPEN_PAYMENTS_CLIENT_SECRET")
    bic           = os.getenv("OPEN_PAYMENTS_BIC")
    psu_id        = os.getenv("OPEN_PAYMENTS_PSU_ID")
    consent_id    = os.getenv("OPEN_PAYMENTS_CONSENT_ID")
    env           = os.getenv("OPEN_PAYMENTS_ENV", "sandbox")

    if all([client_id, client_secret, bic, psu_id, consent_id]):
        try:
            from luna_open_payments.auth import TokenClient
            from luna_open_payments.client import OpenPaymentsClient
            from luna_open_payments.ais import AisService

            tc  = TokenClient(client_id, client_secret, env=env)
            cl  = OpenPaymentsClient(tc, env=env)
            ais = AisService(cl)

            accounts = ais.list_accounts(consent_id, bic, psu_id)
            if accounts:
                date_from = (date.today() - timedelta(days=365)).isoformat()
                txs = ais.get_transactions(
                    account_id=accounts[0].resourceId,
                    consent_id=consent_id,
                    bic_fi=bic,
                    psu_id=psu_id,
                    date_from=date_from,
                    booking_status="booked",
                )
                for tx in txs:
                    if not tx.transactionAmount:
                        continue
                    try:
                        amt = abs(float(D(tx.transactionAmount.amount)))
                    except Exception:
                        continue
                    counterparty = tx.creditorName or tx.debtorName or "Unknown"
                    desc = tx.remittanceInformationUnstructured or ""
                    direction = "outbound" if D(tx.transactionAmount.amount) < 0 else "inbound"
                    bank_rows.append({
                        "tx_id":        tx.transactionId or f"tx-{len(bank_rows)}",
                        "date":         tx.bookingDate or tx.valueDate or "",
                        "counterparty": counterparty,
                        "description":  desc,
                        "amount":       amt,
                        "currency":     tx.transactionAmount.currency or "SEK",
                        "direction":    direction,
                    })
        except Exception as exc:
            print(f"[OpenPayments/match] {exc}")

    if not bank_rows:
        bank_rows = [dict(r) for r in _MOCK_BANK_TXS]

    # ── Zwapgrid → invoices ───────────────────────────────────
    if os.getenv("ZWAPGRID_API_KEY"):
        try:
            from zwapgrid import ZwapgridClient
            from zwapgrid.facts import fetch_money_in

            zw       = ZwapgridClient.from_env()
            money_in = fetch_money_in(zw, lookback_days=365)
            for row in money_in.rows:
                if not row.match_eligible:
                    continue
                invoice_rows.append({
                    "book_id":           row.invoice_id or f"inv-{len(invoice_rows)}",
                    "invoice_reference": row.invoice_reference or row.invoice_id or "",
                    "date":              row.cash_date.isoformat() if row.cash_date else (row.issue_date.isoformat() if row.issue_date else ""),
                    "counterparty":      row.counterparty or "Unknown",
                    "amount":            float(row.cash_amount) if row.cash_amount else 0.0,
                    "currency":          row.currency or "SEK",
                    "direction":         row.direction,
                })
        except Exception as exc:
            print(f"[Zwapgrid/match] {exc}")

    if not invoice_rows:
        invoice_rows = [dict(r) for r in _MOCK_INVOICES]

    return bank_rows, invoice_rows


@app.post("/api/match")
def match_endpoint() -> dict:
    from decimal import Decimal as D
    from verification.match import match_books_to_bank
    from verification.models import BankTxEvent, BookCashEvent
    from datetime import date as date_type

    bank_rows, invoice_rows = _fetch_match_data()

    # Build events for matching
    bank_events: list[BankTxEvent] = []
    for r in bank_rows:
        try:
            d = date_type.fromisoformat(r["date"][:10]) if r["date"] else None
        except ValueError:
            d = None
        if d is None:
            continue
        bank_events.append(BankTxEvent(
            tx_id=r["tx_id"],
            direction=r["direction"],
            amount=D(str(r["amount"])),
            currency=r["currency"],
            booking_date=d,
        ))

    book_events: list[BookCashEvent] = []
    for r in invoice_rows:
        try:
            d = date_type.fromisoformat(r["date"][:10]) if r["date"] else None
        except ValueError:
            d = None
        if d is None:
            continue
        book_events.append(BookCashEvent(
            book_id=r["book_id"],
            invoice_reference=r.get("invoice_reference"),
            direction=r["direction"],
            amount=D(str(r["amount"])),
            currency=r["currency"],
            cash_date=d,
        ))

    report = match_books_to_bank(book_events, bank_events)

    # Build lookup: book_id → outcome
    outcome_by_book: dict[str, object] = {
        o.book_id: o for o in report.outcomes if o.book_id
    }
    # Build lookup: tx_id → matched book_id
    tx_to_book: dict[str, str] = {}
    for o in report.outcomes:
        if o.status == "matched" and o.tx_id and o.book_id:
            tx_to_book[o.tx_id] = o.book_id

    # Enrich display rows with match status
    enriched_bank: list[dict] = []
    for r in bank_rows:
        tx_id = r["tx_id"]
        matched_book = tx_to_book.get(tx_id)
        status = "matched" if matched_book else "unmatched"
        outcome = next((o for o in report.outcomes if o.status == "matched" and o.tx_id == tx_id), None)
        enriched_bank.append({**r, "status": status, "matched_book_id": matched_book, "days_apart": outcome.days_apart if outcome else None})

    enriched_invoices: list[dict] = []
    for r in invoice_rows:
        outcome = outcome_by_book.get(r["book_id"])
        status = outcome.status if outcome else "unmatched"
        enriched_invoices.append({
            **r,
            "status": status,
            "matched_tx_id": outcome.tx_id if outcome and outcome.status == "matched" else None,
            "days_apart":    outcome.days_apart if outcome and outcome.status == "matched" else None,
        })

    return {
        "summary": {
            "eligible":  report.eligible,
            "matched":   report.matched,
            "unmatched": report.unmatched,
            "ambiguous": report.ambiguous,
            "coverage":  report.coverage,
            "flags":     report.flags,
        },
        "bank_transactions": enriched_bank,
        "invoices":          enriched_invoices,
    }
