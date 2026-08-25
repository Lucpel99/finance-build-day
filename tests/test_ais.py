"""
AIS integration tests.

Consent flow:
  1. create_consent → status AwaitingAuthorisation (or equivalent)
  2. In sandbox, some ASPSPs auto-authorise for test PSU IDs.
  3. list_accounts / get_balances require an authorised consent.

Sandbox PSU ID '99990101001' is documented to simulate authorization failures.
Use a valid test PSU ID for your sandbox setup.
"""
import pytest
from datetime import date, timedelta

from luna_open_payments.ais import AisService
from luna_open_payments.models import Consent

SANDBOX_PSU_ID = "199001019876"  # generic sandbox test PSU
VALID_UNTIL = (date.today() + timedelta(days=1)).isoformat()


def test_create_consent_returns_id(ais_service: AisService, test_bic_fi: str):
    consent = ais_service.create_consent(
        bic_fi=test_bic_fi,
        psu_id=SANDBOX_PSU_ID,
        valid_until=VALID_UNTIL,
    )
    assert isinstance(consent, Consent)
    assert consent.consentId
    assert consent.consentStatus


def test_consent_has_awaiting_status(ais_service: AisService, test_bic_fi: str):
    consent = ais_service.create_consent(
        bic_fi=test_bic_fi,
        psu_id=SANDBOX_PSU_ID,
        valid_until=VALID_UNTIL,
    )
    # Freshly created consent should not yet be fully authorised
    assert consent.consentStatus in (
        "received",
        "AwaitingAuthorisation",
        "awaitingAuthorisation",
        "RCVD",
    )


@pytest.fixture(scope="module")
def authorised_consent(ais_service: AisService, test_bic_fi: str):
    """
    Attempt to get an authorised consent.
    In sandbox, some banks auto-authorise. Skip tests if not available.
    """
    consent = ais_service.create_consent(
        bic_fi=test_bic_fi,
        psu_id=SANDBOX_PSU_ID,
        valid_until=VALID_UNTIL,
    )
    if consent.consentStatus.lower() not in ("valid", "accepted"):
        pytest.skip(
            f"Consent status '{consent.consentStatus}' — "
            "full authorisation requires interactive BankID/redirect step in this sandbox bank. "
            "Skipping account/balance tests."
        )
    return consent


def test_list_accounts(ais_service: AisService, test_bic_fi: str, authorised_consent: Consent):
    accounts = ais_service.list_accounts(authorised_consent.consentId, test_bic_fi)
    assert len(accounts) > 0
    for acct in accounts:
        assert acct.resourceId


def test_get_balances(ais_service: AisService, test_bic_fi: str, authorised_consent: Consent):
    accounts = ais_service.list_accounts(authorised_consent.consentId, test_bic_fi)
    assert accounts
    balances = ais_service.get_balances(
        accounts[0].resourceId, authorised_consent.consentId, test_bic_fi
    )
    assert len(balances) > 0
    for b in balances:
        assert b.balanceAmount.currency
        assert b.balanceAmount.amount
