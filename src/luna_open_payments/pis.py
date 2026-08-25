from .client import OpenPaymentsClient
from .models import Payment, PaymentStatus

_SCOPE = "paymentinitiation private"


class PisService:
    def __init__(self, client: OpenPaymentsClient):
        self._client = client

    def initiate_payment(
        self,
        payment_product: str,
        bic_fi: str,
        psu_id: str,
        body: dict,
        *,
        psu_ip_address: str = "127.0.0.1",
    ) -> Payment:
        resp = self._client.post(
            f"/psd2/paymentinitiation/v1/payments/{payment_product}",
            _SCOPE,
            extra_headers={
                "X-BicFi": bic_fi,
                "PSU-ID": psu_id,
                "PSU-IP-Address": psu_ip_address,
            },
            json=body,
        )
        return Payment.model_validate(resp.json())

    def get_payment(
        self, payment_product: str, payment_id: str, bic_fi: str, psu_id: str | None = None
    ) -> Payment:
        headers: dict = {"X-BicFi": bic_fi}
        if psu_id:
            headers["PSU-ID"] = psu_id
        resp = self._client.get(
            f"/psd2/paymentinitiation/v1/payments/{payment_product}/{payment_id}",
            _SCOPE,
            extra_headers=headers,
        )
        return Payment.model_validate(resp.json())

    def get_payment_status(
        self, payment_product: str, payment_id: str, bic_fi: str, psu_id: str | None = None
    ) -> PaymentStatus:
        headers: dict = {"X-BicFi": bic_fi}
        if psu_id:
            headers["PSU-ID"] = psu_id
        resp = self._client.get(
            f"/psd2/paymentinitiation/v1/payments/{payment_product}/{payment_id}/status",
            _SCOPE,
            extra_headers=headers,
        )
        return PaymentStatus.model_validate(resp.json())
