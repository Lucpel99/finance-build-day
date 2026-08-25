from datetime import date
from .client import OpenPaymentsClient
from .models import Account, Balance, Consent, ConsentStatus, Transaction

_SCOPE = "accountinformation private"


class AisService:
    def __init__(self, client: OpenPaymentsClient):
        self._client = client

    def create_consent(
        self,
        bic_fi: str,
        psu_id: str,
        valid_until: str,
        *,
        psu_ip_address: str = "127.0.0.1",
        all_psd2: str = "allAccounts",
        frequency_per_day: int = 4,
    ) -> Consent:
        body = {
            "access": {"allPsd2": all_psd2},
            "recurringIndicator": False,
            "validUntil": valid_until,
            "frequencyPerDay": frequency_per_day,
        }
        resp = self._client.post(
            "/psd2/consent/v1/consents",
            _SCOPE,
            extra_headers={
                "X-BicFi": bic_fi,
                "PSU-ID": psu_id,
                "PSU-IP-Address": psu_ip_address,
            },
            json=body,
        )
        return Consent.model_validate(resp.json())

    def get_consent_status(self, consent_id: str, bic_fi: str) -> ConsentStatus:
        resp = self._client.get(
            f"/psd2/consent/v1/consents/{consent_id}/status",
            _SCOPE,
            extra_headers={"X-BicFi": bic_fi},
        )
        data = resp.json()
        if "consentStatus" not in data:
            data = {"consentStatus": data.get("consentStatus", "unknown")}
        return ConsentStatus.model_validate(data)

    def list_accounts(self, consent_id: str, bic_fi: str) -> list[Account]:
        resp = self._client.get(
            "/psd2/accountinformation/v1/accounts",
            _SCOPE,
            extra_headers={
                "Consent-ID": consent_id,
                "X-BicFi": bic_fi,
            },
        )
        data = resp.json()
        items = data if isinstance(data, list) else data.get("accounts", [])
        return [Account.model_validate(item) for item in items]

    def get_balances(self, account_id: str, consent_id: str, bic_fi: str) -> list[Balance]:
        resp = self._client.get(
            f"/psd2/accountinformation/v1/accounts/{account_id}/balances",
            _SCOPE,
            extra_headers={
                "Consent-ID": consent_id,
                "X-BicFi": bic_fi,
            },
        )
        data = resp.json()
        items = data if isinstance(data, list) else data.get("balances", [])
        return [Balance.model_validate(item) for item in items]

    def get_transactions(
        self,
        account_id: str,
        consent_id: str,
        bic_fi: str,
        date_from: str | None = None,
    ) -> list[Transaction]:
        params = {}
        if date_from:
            params["dateFrom"] = date_from
        resp = self._client.get(
            f"/psd2/accountinformation/v1/accounts/{account_id}/transactions",
            _SCOPE,
            extra_headers={
                "Consent-ID": consent_id,
                "X-BicFi": bic_fi,
            },
            params=params,
        )
        data = resp.json()
        if isinstance(data, list):
            items = data
        else:
            txns = data.get("transactions", {})
            items = txns.get("booked", txns) if isinstance(txns, dict) else txns
        return [Transaction.model_validate(item) for item in items]
