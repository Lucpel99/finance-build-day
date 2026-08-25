from typing import Any
from pydantic import BaseModel, Field


class Aspsp(BaseModel):
    bicFi: str
    name: str
    countryCode: str | None = None
    logoUrl: str | None = None
    capabilities: list[str] = Field(default_factory=list)
    model_config = {"extra": "allow"}


class Country(BaseModel):
    isoCountryCode: str
    name: str | None = None
    model_config = {"extra": "allow"}


class ConsentAccess(BaseModel):
    allPsd2: str | None = None
    accounts: list[dict] | None = None
    balances: list[dict] | None = None
    transactions: list[dict] | None = None


class Consent(BaseModel):
    consentId: str
    consentStatus: str
    access: ConsentAccess | None = None
    validUntil: str | None = None
    model_config = {"extra": "allow"}


class ConsentStatus(BaseModel):
    consentId: str | None = None
    consentStatus: str
    model_config = {"extra": "allow"}


class Account(BaseModel):
    resourceId: str
    iban: str | None = None
    bban: str | None = None
    currency: str | None = None
    name: str | None = None
    product: str | None = None
    cashAccountType: str | None = None
    model_config = {"extra": "allow"}


class Amount(BaseModel):
    currency: str
    amount: str


class Balance(BaseModel):
    balanceType: str | None = None
    balanceAmount: Amount
    creditDebitIndicator: str | None = None
    model_config = {"extra": "allow"}


class Transaction(BaseModel):
    transactionId: str | None = None
    bookingDate: str | None = None
    valueDate: str | None = None
    transactionAmount: Amount | None = None
    creditorName: str | None = None
    debtorName: str | None = None
    remittanceInformationUnstructured: str | None = None
    model_config = {"extra": "allow"}


class PaymentStatus(BaseModel):
    paymentId: str | None = None
    transactionStatus: str
    model_config = {"extra": "allow"}


class Payment(BaseModel):
    paymentId: str | None = None
    transactionStatus: str
    model_config = {"extra": "allow"}
