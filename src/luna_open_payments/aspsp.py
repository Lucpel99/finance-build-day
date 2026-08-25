from .client import OpenPaymentsClient
from .models import Aspsp, Country

_SCOPE = "aspspinformation private"


class AspspService:
    def __init__(self, client: OpenPaymentsClient):
        self._client = client

    def list_aspsps(self, country: str | None = None) -> list[Aspsp]:
        params = {"isoCountryCodes": country} if country else {}
        resp = self._client.get(
            "/psd2/aspspinformation/v1/aspsps",
            _SCOPE,
            params=params,
        )
        data = resp.json()
        items = data if isinstance(data, list) else data.get("aspsps", data.get("aspSPs", []))
        return [Aspsp.model_validate(item) for item in items]

    def get_aspsp(self, bic_fi: str) -> Aspsp:
        resp = self._client.get(
            f"/psd2/aspspinformation/v1/aspsps/{bic_fi}",
            _SCOPE,
        )
        return Aspsp.model_validate(resp.json())

    def list_countries(self) -> list[Country]:
        resp = self._client.get(
            "/psd2/aspspinformation/v1/countries",
            _SCOPE,
        )
        data = resp.json()
        items = data if isinstance(data, list) else data.get("countries", [])
        return [Country.model_validate(item) for item in items]
