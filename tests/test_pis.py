"""
PIS integration tests.

Payment initiation flow:
  1. initiate_payment → transactionStatus Received / RCVD
  2. Authorization (BankID / redirect) is required in sandbox for most banks.
  3. get_payment_status verifies status retrieval.
"""
import pytest
from datetime import date, timedelta

from luna_open_payments.pis import PisService
from luna_open_payments.models import Payment, PaymentStatus

SANDBOX_PSU_ID = "199001019876"
PAYMENT_PRODUCT = "sepa-credit-transfers"

SAMPLE_PAYMENT = {
    "creditorAccount": {"iban": "SE3550000000054910000003"},
    "debtorAccount": {"iban": "SE4550000000058398257466"},
    "creditorName": "Test Creditor",
    "instructedAmount": {"currency": "SEK", "amount": "10.00"},
    "requestedExecutionDate": (date.today() + timedelta(days=1)).isoformat(),
    "remittanceInformationUnstructured": "Integration test payment",
}


def test_initiate_payment_returns_id(pis_service: PisService, test_bic_fi: str):
    payment = pis_service.initiate_payment(
        payment_product=PAYMENT_PRODUCT,
        bic_fi=test_bic_fi,
        psu_id=SANDBOX_PSU_ID,
        body=SAMPLE_PAYMENT,
    )
    assert isinstance(payment, Payment)
    assert payment.paymentId
    assert payment.transactionStatus


def test_payment_initial_status(pis_service: PisService, test_bic_fi: str):
    payment = pis_service.initiate_payment(
        payment_product=PAYMENT_PRODUCT,
        bic_fi=test_bic_fi,
        psu_id=SANDBOX_PSU_ID,
        body=SAMPLE_PAYMENT,
    )
    # Newly created payment should be in a pending/received state
    assert payment.transactionStatus.upper() in (
        "RCVD",
        "RECEIVED",
        "PDNG",
        "ACCP",
        "ACTC",
        "ACWC",
    )


def test_get_payment_status(pis_service: PisService, test_bic_fi: str):
    payment = pis_service.initiate_payment(
        payment_product=PAYMENT_PRODUCT,
        bic_fi=test_bic_fi,
        psu_id=SANDBOX_PSU_ID,
        body=SAMPLE_PAYMENT,
    )
    status = pis_service.get_payment_status(
        PAYMENT_PRODUCT, payment.paymentId, test_bic_fi, psu_id=SANDBOX_PSU_ID
    )
    assert isinstance(status, PaymentStatus)
    assert status.transactionStatus


def test_get_payment_details(pis_service: PisService, test_bic_fi: str):
    payment = pis_service.initiate_payment(
        payment_product=PAYMENT_PRODUCT,
        bic_fi=test_bic_fi,
        psu_id=SANDBOX_PSU_ID,
        body=SAMPLE_PAYMENT,
    )
    fetched = pis_service.get_payment(
        PAYMENT_PRODUCT, payment.paymentId, test_bic_fi, psu_id=SANDBOX_PSU_ID
    )
    assert isinstance(fetched, Payment)
    assert fetched.transactionStatus
