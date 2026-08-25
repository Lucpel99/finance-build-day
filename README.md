# Finance Build Day

Two financial API integrations in one repo, ready to use as Python packages:

- **Luna Open Payments** — PSD2 open banking (account info, payment initiation, bank discovery)
- **Zwapgrid** — Accounting/ERP API (company information)

---

## Setup

**Requirements:** Python 3.11+

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

Copy the env file and fill in your credentials:

```bash
cp .env.example .env
```

```ini
# Open Payments — get these from the Open Banking Platform developer portal
OPEN_PAYMENTS_CLIENT_ID=your-client-id
OPEN_PAYMENTS_CLIENT_SECRET=your-client-secret
OPEN_PAYMENTS_ENV=sandbox          # or "production"

# Zwapgrid — get these from the Zwapgrid console
ZWAPGRID_API_KEY=your-api-key
ZWAPGRID_CONSENT_ID=your-consent-id
```

---

## Running the Tests

```bash
pytest -v
```

The test suite covers both integrations. Tests that require live API credentials skip automatically if the relevant env vars are not set — so you can always run the full suite and only the tests for the credentials you have will execute.

To run tests for a specific integration:

```bash
pytest tests/test_zwapgrid.py -v       # Zwapgrid tests
pytest tests/test_aspsp.py -v          # Open Payments — bank discovery
pytest tests/test_auth.py -v           # Open Payments — OAuth token
pytest tests/test_ais.py -v            # Open Payments — account info
pytest tests/test_pis.py -v            # Open Payments — payment initiation
```

One test always runs without credentials — it validates that bad credentials produce the correct error:

```bash
pytest tests/test_zwapgrid.py::test_invalid_key_raises_zwapgrid_error -v
```

---

## Zwapgrid

Retrieves company information from the Zwapgrid Accounting API.

### Initialisation

```python
from zwapgrid import ZwapgridClient

# From environment variables (recommended)
client = ZwapgridClient.from_env()

# Or explicitly
client = ZwapgridClient(api_key="...", consent_id="...")
```

### Methods

#### `get_company_information() -> dict`

Returns the company information associated with the consent.

```python
info = client.get_company_information()
print(info)
# {"companyName": "Acme AB", "organizationNumber": "5591234567", ...}
```

**Endpoint:** `GET https://apione.zwapgrid.com/accounting/api/v1/consents/{consent_id}/companyinformation`

### Error handling

```python
from zwapgrid import ZwapgridClient, ZwapgridError

try:
    info = client.get_company_information()
except ZwapgridError as e:
    print(e.status_code, e.body)
```

---

## Luna Open Payments

PSD2-compliant open banking SDK. Supports sandbox and production environments.

### Initialisation

```python
from dotenv import load_dotenv
import os

from luna_open_payments.auth import TokenClient
from luna_open_payments.client import OpenPaymentsClient
from luna_open_payments.aspsp import AspspService
from luna_open_payments.ais import AisService
from luna_open_payments.pis import PisService

load_dotenv()

token_client = TokenClient(
    client_id=os.environ["OPEN_PAYMENTS_CLIENT_ID"],
    client_secret=os.environ["OPEN_PAYMENTS_CLIENT_SECRET"],
    env="sandbox",   # or "production"
)
client = OpenPaymentsClient(token_client, env="sandbox")

aspsp_service = AspspService(client)
ais_service   = AisService(client)
pis_service   = PisService(client)
```

OAuth2 tokens are fetched automatically and cached per scope until 60 seconds before expiry.

---

### ASPSP Service — Bank Discovery

#### `list_aspsps(country=None) -> list[Aspsp]`

Lists all supported banks. Optionally filter by ISO country code.

```python
banks = aspsp_service.list_aspsps()
swedish_banks = aspsp_service.list_aspsps(country="SE")

for bank in banks:
    print(bank.bicFi, bank.name, bank.countryCode)
```

**Endpoint:** `GET /psd2/aspspinformation/v1/aspsps`

#### `get_aspsp(bic_fi) -> Aspsp`

Returns a single bank by its BIC.

```python
bank = aspsp_service.get_aspsp("HANDSESS")
print(bank.name, bank.logoUrl)
```

**Endpoint:** `GET /psd2/aspspinformation/v1/aspsps/{bic_fi}`

#### `list_countries() -> list[Country]`

Lists all countries that have at least one supported bank.

```python
countries = aspsp_service.list_countries()
for c in countries:
    print(c.isoCountryCode, c.name)
```

**Endpoint:** `GET /psd2/aspspinformation/v1/countries`

---

### AIS Service — Account Information

Requires a **consent** authorised by the PSU (bank customer) before account data can be accessed.

#### `create_consent(bic_fi, psu_id, valid_until, ...) -> Consent`

Creates an account access consent for a PSU at a specific bank.

```python
consent = ais_service.create_consent(
    bic_fi="HANDSESS",
    psu_id="199001019876",
    valid_until="2026-12-31",
)
print(consent.consentId, consent.consentStatus)
```

| Parameter | Description | Default |
|-----------|-------------|---------|
| `bic_fi` | Bank BIC | required |
| `psu_id` | PSU's personal/corporate ID | required |
| `valid_until` | Consent expiry date (`YYYY-MM-DD`) | required |
| `psu_ip_address` | PSU's IP address | `"127.0.0.1"` |
| `all_psd2` | Consent scope | `"allAccounts"` |
| `frequency_per_day` | Max daily calls | `4` |

**Endpoint:** `POST /psd2/consent/v1/consents`

#### `get_consent_status(consent_id, bic_fi) -> ConsentStatus`

Checks whether a consent has been authorised by the PSU. In sandbox, some banks auto-authorise.

```python
status = ais_service.get_consent_status(consent.consentId, bic_fi="HANDSESS")
print(status.consentStatus)   # "valid", "received", "rejected", ...
```

**Endpoint:** `GET /psd2/consent/v1/consents/{consent_id}/status`

#### `list_accounts(consent_id, bic_fi) -> list[Account]`

Lists all accounts the PSU has granted access to.

```python
accounts = ais_service.list_accounts(consent.consentId, bic_fi="HANDSESS")
for acc in accounts:
    print(acc.resourceId, acc.iban, acc.currency)
```

**Endpoint:** `GET /psd2/accountinformation/v1/accounts`

#### `get_balances(account_id, consent_id, bic_fi) -> list[Balance]`

Returns all balances for a given account.

```python
balances = ais_service.get_balances(
    account_id=accounts[0].resourceId,
    consent_id=consent.consentId,
    bic_fi="HANDSESS",
)
for b in balances:
    print(b.balanceType, b.balanceAmount.amount, b.balanceAmount.currency)
```

**Endpoint:** `GET /psd2/accountinformation/v1/accounts/{account_id}/balances`

#### `get_transactions(account_id, consent_id, bic_fi, date_from=None) -> list[Transaction]`

Returns booked transactions. Optionally filter by start date (`YYYY-MM-DD`).

```python
transactions = ais_service.get_transactions(
    account_id=accounts[0].resourceId,
    consent_id=consent.consentId,
    bic_fi="HANDSESS",
    date_from="2026-01-01",
)
for tx in transactions:
    print(tx.bookingDate, tx.transactionAmount.amount, tx.remittanceInformationUnstructured)
```

**Endpoint:** `GET /psd2/accountinformation/v1/accounts/{account_id}/transactions`

---

### PIS Service — Payment Initiation

#### `initiate_payment(payment_product, bic_fi, psu_id, body, ...) -> Payment`

Initiates a payment. The most common `payment_product` is `"sepa-credit-transfers"`.

```python
payment = pis_service.initiate_payment(
    payment_product="sepa-credit-transfers",
    bic_fi="HANDSESS",
    psu_id="199001019876",
    body={
        "creditorAccount": {"iban": "SE3550000000054910000003"},
        "creditorName": "Jane Doe",
        "instructedAmount": {"currency": "SEK", "amount": "100.00"},
        "debtorAccount": {"iban": "SE3550000000054910000003"},
    },
)
print(payment.paymentId, payment.transactionStatus)
```

**Endpoint:** `POST /psd2/paymentinitiation/v1/payments/{payment_product}`

#### `get_payment(payment_product, payment_id, bic_fi, psu_id=None) -> Payment`

Retrieves full details of a payment.

```python
payment = pis_service.get_payment(
    payment_product="sepa-credit-transfers",
    payment_id=payment.paymentId,
    bic_fi="HANDSESS",
)
```

**Endpoint:** `GET /psd2/paymentinitiation/v1/payments/{payment_product}/{payment_id}`

#### `get_payment_status(payment_product, payment_id, bic_fi, psu_id=None) -> PaymentStatus`

Polls the status of a payment.

```python
status = pis_service.get_payment_status(
    payment_product="sepa-credit-transfers",
    payment_id=payment.paymentId,
    bic_fi="HANDSESS",
)
print(status.transactionStatus)   # "ACCP", "ACSC", "RJCT", ...
```

**Endpoint:** `GET /psd2/paymentinitiation/v1/payments/{payment_product}/{payment_id}/status`

---

### Error handling

All services raise `APIError` on non-2xx responses and `AuthError` if token acquisition fails.

```python
from luna_open_payments.client import APIError
from luna_open_payments.auth import AuthError

try:
    accounts = ais_service.list_accounts(consent_id, bic_fi)
except APIError as e:
    print(e.status_code, e.body)
except AuthError as e:
    print("Token error:", e)
```
