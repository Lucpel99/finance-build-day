import os
from datetime import timedelta

import pytest
from dotenv import load_dotenv

from zwapgrid import (
    ClaimedOnboarding,
    ZwapgridClient,
    ZwapgridError,
    build_claim_report,
    fetch_identity,
    fetch_money_in,
    fetch_money_out,
)
from zwapgrid.client import invoice_date_param
from zwapgrid.facts import lookback_window

load_dotenv()


@pytest.fixture(scope="session")
def zwapgrid_client() -> ZwapgridClient:
    api_key = os.environ.get("ZWAPGRID_API_KEY")
    consent_id = os.environ.get("ZWAPGRID_CONSENT_ID")
    if not api_key or not consent_id:
        pytest.skip("ZWAPGRID_API_KEY and ZWAPGRID_CONSENT_ID not set")
    return ZwapgridClient(api_key=api_key, consent_id=consent_id)


def test_get_company_information_returns_dict(zwapgrid_client: ZwapgridClient):
    result = zwapgrid_client.get_company_information()
    assert isinstance(result, dict)


def test_get_income_statement_returns_dict(zwapgrid_client: ZwapgridClient):
    result = zwapgrid_client.get_income_statement()
    assert isinstance(result, dict)
    assert "financialReport" in result or "accountBalancePeriod" in result


def test_get_balance_sheet_returns_dict(zwapgrid_client: ZwapgridClient):
    result = zwapgrid_client.get_balance_sheet()
    assert isinstance(result, dict)
    assert "financialReport" in result or "accountBalancePeriod" in result


def test_get_trial_balances_returns_dict(zwapgrid_client: ZwapgridClient):
    start, end = lookback_window(180)
    result = zwapgrid_client.get_trial_balances(
        start_date=start.isoformat(),
        end_date=end.isoformat(),
    )
    assert isinstance(result, dict)
    assert "financialReport" in result or "trialBalancePeriod" in result


def test_list_sales_invoices_uses_date_only_and_pages(zwapgrid_client: ZwapgridClient):
    start, end = lookback_window(365)
    result = zwapgrid_client.list_sales_invoices(
        count=10,
        include="paymentStatus",
        from_invoice_date=f"{start.isoformat()}T00:00:00Z",
        to_invoice_date=end.isoformat(),
    )
    assert "data" in result or "meta" in result
    meta = result.get("meta") or {}
    assert meta.get("currentPage", 1) >= 1


def test_supplier_list_does_not_501_when_order_by_passed(zwapgrid_client: ZwapgridClient):
    start, end = lookback_window(365)
    result = zwapgrid_client.list_supplier_invoices(
        count=10,
        include="paymentStatus",
        from_invoice_date=start.isoformat(),
        to_invoice_date=end.isoformat(),
        order_by="DateAscending",
    )
    assert "data" in result or "meta" in result


def test_list_sales_invoice_payments_returns_paged_result(zwapgrid_client: ZwapgridClient):
    result = zwapgrid_client.list_sales_invoice_payments()
    assert isinstance(result, dict)
    assert "data" in result or "meta" in result


def test_list_supplier_invoice_payments_returns_paged_result(zwapgrid_client: ZwapgridClient):
    result = zwapgrid_client.list_supplier_invoice_payments()
    assert isinstance(result, dict)
    assert "data" in result or "meta" in result


def test_fetch_identity(zwapgrid_client: ZwapgridClient):
    facts = fetch_identity(zwapgrid_client)
    assert facts.legal_name or facts.trading_name or facts.organization_number


def test_fetch_money_in_completes_on_seed(zwapgrid_client: ZwapgridClient):
    facts = fetch_money_in(zwapgrid_client)
    assert facts.complete is True
    assert facts.total_resources >= 0
    assert facts.window_end - facts.window_start >= timedelta(days=360)
    if facts.rows:
        assert facts.rows[0].direction == "inbound"


def test_fetch_money_out_completes_on_seed(zwapgrid_client: ZwapgridClient):
    facts = fetch_money_out(zwapgrid_client)
    assert facts.complete is True
    if facts.rows:
        assert facts.rows[0].direction == "outbound"


def test_claim_report_seed_is_insufficient_history(zwapgrid_client: ZwapgridClient):
    money_in = fetch_money_in(zwapgrid_client)
    money_out = fetch_money_out(zwapgrid_client)
    identity = fetch_identity(zwapgrid_client)
    report = build_claim_report(
        zwapgrid_client,
        ClaimedOnboarding(yearly_revenue=1_000_000),
        money_in,
        money_out,
        identity,
    )
    assert report.freshness in ("fresh", "ageing", "stale", "dormant")
    revenue = next(s for s in report.claim_vs_books if s.metric == "yearly_revenue")
    if money_in.total_resources <= 1:
        assert revenue.confidence <= 0.25 or "insufficient_history" in revenue.flags


def test_invalid_key_raises_zwapgrid_error():
    client = ZwapgridClient(api_key="invalid", consent_id="invalid")
    with pytest.raises(ZwapgridError) as exc_info:
        client.get_company_information()
    assert exc_info.value.status_code in (401, 403)


def test_invoice_date_param_exported():
    assert invoice_date_param("2025-08-25T12:00:00Z") == "2025-08-25"
