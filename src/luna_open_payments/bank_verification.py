from decimal import Decimal, InvalidOperation


def normalize_iban(iban: str | None) -> str | None:
    if not iban:
        return None

    return iban.replace(" ", "").upper()


def normalize_name(name: str | None) -> str | None:
    if not name:
        return None

    return " ".join(name.lower().split())


def get_business_accounts(accounts):
    business_accounts = []

    for account in accounts:
        raw = account.model_dump()

        if raw.get("usage") == "ORGA":
            business_accounts.append(account)

    return business_accounts


def verify_declared_iban(
    declared_iban: str,
    accounts,
):
    declared = normalize_iban(declared_iban)

    matched_account = None

    for account in accounts:
        account_iban = normalize_iban(account.iban)

        if account_iban == declared:
            matched_account = account
            break

    if not matched_account:
        return {
            "declared_iban": declared,
            "verified": False,
            "reason": "Declared IBAN was not found among connected business accounts",
        }

    raw = matched_account.model_dump()

    return {
        "declared_iban": declared,
        "verified": True,
        "resource_id": matched_account.resourceId,
        "account_name": matched_account.name,
        "currency": matched_account.currency,
        "owner_name": raw.get("ownerName"),
        "usage": raw.get("usage"),
    }


def verify_owner_name(
    declared_company_name: str,
    account,
):
    raw = account.model_dump()

    bank_owner_name = raw.get("ownerName")

    declared_normalized = normalize_name(
        declared_company_name
    )

    owner_normalized = normalize_name(
        bank_owner_name
    )

    matches = (
        declared_normalized is not None
        and owner_normalized is not None
        and declared_normalized == owner_normalized
    )

    return {
        "declared_company_name": declared_company_name,
        "bank_owner_name": bank_owner_name,
        "matches": matches,
    }


def calculate_transaction_metrics(transactions):
    incoming_total = Decimal("0")
    outgoing_total = Decimal("0")

    incoming_count = 0
    outgoing_count = 0

    incoming_transactions = []
    outgoing_transactions = []

    for tx in transactions:
        if not tx.transactionAmount:
            continue

        try:
            amount = Decimal(
                tx.transactionAmount.amount
            )
        except (InvalidOperation, TypeError):
            continue

        if amount > 0:
            incoming_total += amount
            incoming_count += 1
            incoming_transactions.append(tx)

        elif amount < 0:
            outgoing_total += abs(amount)
            outgoing_count += 1
            outgoing_transactions.append(tx)

    average_incoming = (
        incoming_total / incoming_count
        if incoming_count > 0
        else Decimal("0")
    )

    average_outgoing = (
        outgoing_total / outgoing_count
        if outgoing_count > 0
        else Decimal("0")
    )

    net_cash_flow = (
        incoming_total - outgoing_total
    )

    return {
        "transaction_count":
            incoming_count + outgoing_count,

        "incoming_transaction_count":
            incoming_count,

        "outgoing_transaction_count":
            outgoing_count,

        "incoming_total":
            float(incoming_total),

        "outgoing_total":
            float(outgoing_total),

        "net_cash_flow":
            float(net_cash_flow),

        "average_incoming_transaction":
            float(average_incoming),

        "average_outgoing_transaction":
            float(average_outgoing),
    }


def percentage_difference(
    declared_value: float,
    observed_value: float,
):
    if declared_value == 0:
        return None

    difference = abs(
        observed_value - declared_value
    )

    return (
        difference / declared_value
    ) * 100


def compare_declared_value(
    declared_value: float,
    observed_value: float,
    tolerance_percent: float = 10.0,
):
    difference_percent = percentage_difference(
        declared_value,
        observed_value,
    )

    if difference_percent is None:
        status = "UNKNOWN"
    elif difference_percent <= tolerance_percent:
        status = "MATCH"
    else:
        status = "MISMATCH"

    return {
        "declared": declared_value,
        "observed": observed_value,
        "difference_percent": (
            round(difference_percent, 2)
            if difference_percent is not None
            else None
        ),
        "status": status,
    }