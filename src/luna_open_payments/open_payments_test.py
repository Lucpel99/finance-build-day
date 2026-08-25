import os
from datetime import date, timedelta

from dotenv import load_dotenv

from luna_open_payments.auth import TokenClient
from luna_open_payments.client import OpenPaymentsClient
from luna_open_payments.ais import AisService

from luna_open_payments.bank_verification import (
    get_business_accounts,
    verify_declared_iban,
    verify_owner_name,
    calculate_transaction_metrics,
    compare_declared_value,
)


# --------------------------------------------------
# LOAD ENV
# --------------------------------------------------

load_dotenv()

CLIENT_ID = os.getenv(
    "OPEN_PAYMENTS_CLIENT_ID"
)

CLIENT_SECRET = os.getenv(
    "OPEN_PAYMENTS_CLIENT_SECRET"
)

BIC = os.getenv(
    "OPEN_PAYMENTS_BIC"
)

PSU_ID = os.getenv(
    "OPEN_PAYMENTS_PSU_ID"
)

CONSENT_ID = os.getenv(
    "OPEN_PAYMENTS_CONSENT_ID"
)


# --------------------------------------------------
# TEST MERCHANT DECLARATIONS
# --------------------------------------------------

DECLARED_COMPANY_NAME = (
    "Andersson Trading AB"
)

DECLARED_IBAN = (
    "SE8050000000052131234567"
)

DECLARED_AVERAGE_TRANSACTION_VALUE = (
    15000.00
)


# --------------------------------------------------
# VALIDATE
# --------------------------------------------------

if not CLIENT_ID:
    raise Exception(
        "OPEN_PAYMENTS_CLIENT_ID missing"
    )

if not CLIENT_SECRET:
    raise Exception(
        "OPEN_PAYMENTS_CLIENT_SECRET missing"
    )

if not BIC:
    raise Exception(
        "OPEN_PAYMENTS_BIC missing"
    )

if not PSU_ID:
    raise Exception(
        "OPEN_PAYMENTS_PSU_ID missing"
    )

if not CONSENT_ID:
    raise Exception(
        "OPEN_PAYMENTS_CONSENT_ID missing"
    )


# --------------------------------------------------
# CLIENT
# --------------------------------------------------

token_client = TokenClient(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    env="sandbox"
)

client = OpenPaymentsClient(
    token_client=token_client,
    env="sandbox"
)

ais = AisService(client)


# --------------------------------------------------
# CHECK CONSENT
# --------------------------------------------------

status = ais.get_consent_status(
    consent_id=CONSENT_ID,
    bic_fi=BIC,
    psu_id=PSU_ID
)

if status.consentStatus != "valid":
    raise Exception(
        f"Consent is not valid: "
        f"{status.consentStatus}"
    )


# --------------------------------------------------
# GET ACCOUNTS
# --------------------------------------------------

accounts = ais.list_accounts(
    consent_id=CONSENT_ID,
    bic_fi=BIC,
    psu_id=PSU_ID
)

business_accounts = (
    get_business_accounts(accounts)
)


print("\n================================")
print("MERCHANT BANK VERIFICATION")
print("================================")


# --------------------------------------------------
# VERIFY IBAN
# --------------------------------------------------

iban_result = verify_declared_iban(
    DECLARED_IBAN,
    business_accounts,
)

print("\nBANK ACCOUNT")

print(
    "Declared IBAN:",
    DECLARED_IBAN
)

print(
    "Verified:",
    iban_result["verified"]
)

if not iban_result["verified"]:
    raise Exception(
        "Declared merchant account "
        "was not found"
    )


# --------------------------------------------------
# FIND MATCHED ACCOUNT
# --------------------------------------------------

matched_account = None

for account in business_accounts:
    if (
        account.resourceId
        == iban_result["resource_id"]
    ):
        matched_account = account
        break


# --------------------------------------------------
# VERIFY OWNER
# --------------------------------------------------

owner_result = verify_owner_name(
    DECLARED_COMPANY_NAME,
    matched_account,
)

print("\nACCOUNT OWNERSHIP")

print(
    "Declared company:",
    owner_result[
        "declared_company_name"
    ]
)

print(
    "Bank owner:",
    owner_result[
        "bank_owner_name"
    ]
)

print(
    "Owner matches:",
    owner_result["matches"]
)


# --------------------------------------------------
# BALANCE
# --------------------------------------------------

balances = ais.get_balances(
    account_id=matched_account.resourceId,
    consent_id=CONSENT_ID,
    bic_fi=BIC,
    psu_id=PSU_ID,
)

print("\nBALANCES")

for balance in balances:
    print(
        balance.balanceType,
        balance.balanceAmount.amount,
        balance.balanceAmount.currency,
    )


# --------------------------------------------------
# TRANSACTIONS
# --------------------------------------------------

date_from = (
    date.today()
    - timedelta(days=365)
).isoformat()

transactions = ais.get_transactions(
    account_id=matched_account.resourceId,
    consent_id=CONSENT_ID,
    bic_fi=BIC,
    psu_id=PSU_ID,
    date_from=date_from,
    booking_status="booked",
)

metrics = calculate_transaction_metrics(
    transactions
)


print("\nTRANSACTION METRICS")

print(
    "Transactions:",
    metrics["transaction_count"]
)

print(
    "Incoming count:",
    metrics[
        "incoming_transaction_count"
    ]
)

print(
    "Outgoing count:",
    metrics[
        "outgoing_transaction_count"
    ]
)

print(
    "Incoming total:",
    metrics["incoming_total"]
)

print(
    "Outgoing total:",
    metrics["outgoing_total"]
)

print(
    "Net cash flow:",
    metrics["net_cash_flow"]
)

print(
    "Average incoming transaction:",
    metrics[
        "average_incoming_transaction"
    ]
)


# --------------------------------------------------
# CROSS-CHECK DECLARED AVERAGE
# --------------------------------------------------

average_check = compare_declared_value(
    DECLARED_AVERAGE_TRANSACTION_VALUE,
    metrics[
        "average_incoming_transaction"
    ],
    tolerance_percent=10.0,
)

print("\nAVERAGE TRANSACTION CHECK")

print(
    "Declared:",
    average_check["declared"]
)

print(
    "Observed:",
    average_check["observed"]
)

print(
    "Difference:",
    average_check[
        "difference_percent"
    ],
    "%"
)

print(
    "Status:",
    average_check["status"]
)


# --------------------------------------------------
# FINAL SUMMARY
# --------------------------------------------------

print("\n================================")
print("VERIFICATION SUMMARY")
print("================================")

print(
    "Bank account verified:",
    iban_result["verified"]
)

print(
    "Account ownership matches:",
    owner_result["matches"]
)

print(
    "Average transaction check:",
    average_check["status"]
)