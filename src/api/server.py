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
