import uuid
import httpx

ZWAPGRID_BASE_URL = "https://apione.zwapgrid.com"


class ZwapgridError(Exception):
    def __init__(self, status_code: int, body: str):
        super().__init__(f"Zwapgrid API error [{status_code}]: {body}")
        self.status_code = status_code
        self.body = body


class ZwapgridClient:
    def __init__(self, api_key: str, consent_id: str):
        self._api_key = api_key
        self._consent_id = consent_id

    @classmethod
    def from_env(cls) -> "ZwapgridClient":
        import os
        return cls(
            api_key=os.environ["ZWAPGRID_API_KEY"],
            consent_id=os.environ["ZWAPGRID_CONSENT_ID"],
        )

    def _headers(self) -> dict[str, str]:
        return {
            "x-api-key": self._api_key,
            "x-correlation-id": str(uuid.uuid4()),
            "Accept": "application/json",
        }

    def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        response = httpx.request(
            method,
            ZWAPGRID_BASE_URL + path,
            headers=self._headers(),
            timeout=30,
            **kwargs,
        )
        if not response.is_success:
            raise ZwapgridError(response.status_code, response.text)
        return response

    def get_company_information(self) -> dict:
        path = f"/accounting/api/v1/consents/{self._consent_id}/companyinformation"
        return self._request("GET", path).json()
