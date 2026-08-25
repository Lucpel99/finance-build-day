# Finance Build Day

Two financial API integrations in one repo, ready to use as Python packages:

- **Luna Open Payments** — PSD2 open banking (account info, payment initiation, bank discovery)
- **Zwapgrid** — Accounting/ERP API (identity, statements, invoices, payments)

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

Accounting data for onboarding verification. All reads are scoped to the connected consent.

**AIS** in this repo is Luna Account Information Service (bank accounts and booked transactions). Zwapgrid does not import it. Identity, money-in/out, and claim-vs-books scores live in `zwapgrid`. Books-vs-bank matching lives in the shared `verification` package (imports neither SDK). Claim-vs-bank is still the open-banking lane.

### Fortnox notes

Invoice date filters must be `yyyy-MM-dd`. ISO datetimes (`2025-08-25T00:00:00Z`) return Fortnox `2000302`. `list_sales_invoices` / `list_supplier_invoices` coerce dates automatically. Do **not** send `OrderBy` on supplier invoices (HTTP 501); the client drops it.

A 12-month window is requested on every list call; `meta.totalResources` / `totalPages` tell you whether the page set is complete. Seed consents may only have one invoice of each type.

### Verification entry points

```python
from datetime import date
from zwapgrid import (
    ZwapgridClient,
    ClaimedOnboarding,
    fetch_identity,
    fetch_money_in,
    fetch_money_out,
    build_claim_report,
    as_book_events,
    needles_match_haystack,
)

client = ZwapgridClient.from_env()
identity = fetch_identity(client)
money_in = fetch_money_in(client, lookback_days=365)
money_out = fetch_money_out(client, lookback_days=365)
report = build_claim_report(
    client,
    ClaimedOnboarding(
        yearly_revenue=2_400_000,
        average_transaction=8_000,
        max_transaction=80_000,
    ),
    money_in,
    money_out,
    identity,
    connected_account_ids=["SE4550000000058398257466"],  # from AIS, optional
)

from luna_open_payments import as_bank_events
from verification import match_books_to_bank

books = as_book_events(money_in, money_out)
bank, flags = as_bank_events(transactions)  # from AisService.get_transactions(..., date_from=365 days ago)
zb = match_books_to_bank(books, bank, flags=flags)
# Live sandboxes are different companies: expect eligible=2, matched=0

# Bank-account overlap (AIS teammate): identity.bank_accounts[].normalized vs AIS iban/bban
# Remittance needles exist on cash rows but are not a Z→B gate in v1
needles_match_haystack(money_in.rows[0].remittance_needles, "BETALNING INV-001 PAY-59")
```

Each cash row carries `cash_amount`, `currency`, `cash_date` + `cash_date_source`, `normalized_counterparty`, `amount_unique_in_window`, `remittance_needles`. Paid leftover rounding (`-0.25` remaining with `FULLY_PAID`) is ignored; cash amount is the payment or the tax-inclusive total.

| Compare | Zwapgrid fields | AIS fields |
|---------|-----------------|------------|
| Legal identity | `legal_name`, `organization_number` (`SE:ORGNR`), address | UI form (AIS has no orgnr) |
| Bank accounts | `paymentMeans.financialAccount.id` | `Account.iban` / `bban` |
| Money in | sales invoices + `/salesinvoices/{id}/payments` | inbound credits |
| Money out | supplier invoices + `/supplierinvoices/{id}/payments` | debits (`creditDebitIndicator=DBIT`) |
| Remittance | `invoice.reference`, payment `reference`, `paymentIds` | unstructured + structured remittance, `endToEndId` |
| Revenue claim | `incomestatement` fiscal-year series (not a rolling P&L) | inbound credit volume (teammate) |

Claim scores have **agreement** and **confidence** separately. Freshness (`fresh` / `ageing` / `stale` / `dormant`) caps confidence when books are old.

**Yearly revenue is pick-one, not a blend.** Each income-statement period stores raw `revenue` and `annualized = revenue × 365 / days`. Scoring then chooses a single observed: last closed year (`days ≥ 300`, unannualized) if one exists; else YTD annualized; else raw YTD with `insufficient_history` when `days < 90`. Sparse invoices (`n < 5`) also cap confidence. Trailing-12-month invoice sum (`invoice_revenue`) is already a year and is not annualized. We do not blend prior year with YTD.

### Books → bank (Z → B)

Paid invoices should appear as a booked AIS transaction. Unmatched **bank** lines are ignored (payroll, tax, fees, transfers, PSP nets). Do not require B → Z coverage.

Gates (all must hold; one-to-one):

1. Exact `cash_amount` (payment sum, else tax-inclusive)
2. Exact currency
3. Same direction (sales → credit, supplier → debit)
4. `|cash_date − bookingDate| ≤ 5` days (`cash_date` is paid/received/booked/settlement, not `issueDate`)
5. Bank tx not already consumed

Closest date wins; a tie is `ambiguous` and does not consume the tx. Unique-amount rows are claimed first.

Live Fortnox vs Luna sandboxes are different companies. Expected result is **0/2** (`3281.25` SEK in, `2687.50` SEK out unmatched). That is a correct miss, not a fixture gap.

`AisService.get_transactions` does not paginate. A 365-day pull may be truncated by the ASPSP; do not treat the list as complete. Direction mapping: `creditDebitIndicator` first; signed amounts only if the batch has a negative; unsigned all-positive txs with no indicator are skipped (`unsigned_amount_no_indicator`). Split settlements (one invoice, two bank credits) miss in v1 because we match the summed `cash_amount`.

### Raw client methods

| Method | Endpoint | What we derive |
|--------|----------|----------------|
| `get_company_information()` | `GET /companyinformation` | Legal/accounting identity |
| `get_income_statement()` | `GET /incomestatement` | Revenue, expenses, profit |
| `get_balance_sheet()` | `GET /balancesheet` | Assets, liabilities, equity |
| `get_trial_balances()` | `GET /trialbalances` (v2) | Underlying ledger balances |
| `list_sales_invoices()` / `iter_sales_invoices()` | `GET /salesinvoices` | Trading activity (paged) |
| `get_sales_invoice(id)` | `GET /salesinvoices/{id}` | Full invoice (OCR / paymentMeans) |
| `list_sales_invoice_payments_for_invoice(id)` | `GET /salesinvoices/{id}/payments` | Paid receivables for one invoice |
| `list_sales_invoice_payments()` | `GET /salesinvoices/payments` | All sales payments |
| `list_supplier_invoices()` / `iter_supplier_invoices()` | `GET /supplierinvoices` | Cost/business activity |
| `get_supplier_invoice(id)` | `GET /supplierinvoices/{id}` | Full supplier invoice |
| `list_supplier_invoice_payments_for_invoice(id)` | `GET /supplierinvoices/{id}/payments` | Payments we made |
| `list_supplier_invoice_payments()` | `GET /supplierinvoices/payments` | All supplier payments |

Invoice `FromInvoiceDate` / `ToInvoiceDate` filter **`issueDate`**, not payment date. Max 100 rows per page.

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

Legal/accounting identity for the connected company.

```python
info = client.get_company_information()
```

**Endpoint:** `GET /accounting/api/v1/consents/{consent_id}/companyinformation`

#### `get_income_statement(*, start_date=None, end_date=None, level=None) -> dict`

Revenue, expenses, and profit. Dates are ISO 8601 (`yyyy-MM-ddTHH:mm:ssZ`). If `start_date` is omitted, Zwapgrid defaults to the start of the current fiscal year. `level` is heading depth 1–5.

```python
pnl = client.get_income_statement(start_date="2026-01-01T00:00:00Z")
```

**Endpoint:** `GET /accounting/api/v1/consents/{consent_id}/incomestatement`

#### `get_balance_sheet(*, end_date=None, level=None) -> dict`

Assets, liabilities, and equity at a point in time.

```python
sheet = client.get_balance_sheet(end_date="2026-08-25T00:00:00Z")
```

**Endpoint:** `GET /accounting/api/v1/consents/{consent_id}/balancesheet`

#### `get_trial_balances(*, start_date=None, end_date=None, level=None) -> dict`

Underlying ledger balances (trial balance v2). Dates are `yyyy-MM-dd`. Fortnox allows at most 6 months between `StartDate` and `EndDate`.

```python
tb = client.get_trial_balances(start_date="2026-01-01", end_date="2026-08-25")
```

**Endpoint:** `GET /accounting/api/v2/consents/{consent_id}/trialbalances`

#### `list_sales_invoices(*, count=None, current_page=None, from_invoice_date=None, to_invoice_date=None, status=None, order_by=None, include=None) -> dict`

Issued sales invoices (trading activity). Paginated (`data` + `meta`).

`status`: `Paid`, `Unpaid`, `Overdue`, `Cancelled`, `Unbooked`, `Unsent`, `Draft`.  
`order_by`: `DateDescending` or `DateAscending`.  
`include`: e.g. `"paymentStatus"`.

```python
invoices = client.list_sales_invoices(count=50, include="paymentStatus")
```

**Endpoint:** `GET /accounting/api/v1/consents/{consent_id}/salesinvoices`

#### `list_sales_invoice_payments() -> dict`

Paid receivables across sales invoices. Paginated.

```python
payments = client.list_sales_invoice_payments()
```

**Endpoint:** `GET /accounting/api/v1/consents/{consent_id}/salesinvoices/payments`

#### `list_supplier_invoices(*, count=None, current_page=None, from_invoice_date=None, to_invoice_date=None, status=None, order_by=None, include=None) -> dict`

Supplier invoices (cost / business activity). Paginated.

`status`: `IsSold`, `Paid`, `Unpaid`, `Overdue`, `Cancelled`, `Unsent`.

```python
bills = client.list_supplier_invoices(count=50, include="paymentStatus")
```

**Endpoint:** `GET /accounting/api/v1/consents/{consent_id}/supplierinvoices`

#### `list_supplier_invoice_payments() -> dict`

Supplier-payment behaviour across supplier invoices. Paginated.

```python
supplier_payments = client.list_supplier_invoice_payments()
```

**Endpoint:** `GET /accounting/api/v1/consents/{consent_id}/supplierinvoices/payments`

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

Returns booked transactions. Optionally filter by start date (`YYYY-MM-DD`). Does **not** paginate — a 365-day window may be truncated by the ASPSP.

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
