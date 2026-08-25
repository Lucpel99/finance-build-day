import uuid
import httpx

from .auth import TokenClient

API_BASE_URLS = {
    "sandbox": "https://api.sandbox.openbankingplatform.com",
    "production": "https://api.openbankingplatform.com",
}


class APIError(Exception):
    def __init__(self, status_code: int, body: str):
        super().__init__(f"API error [{status_code}]: {body}")
        self.status_code = status_code
        self.body = body


class OpenPaymentsClient:
    def __init__(self, token_client: TokenClient, env: str = "sandbox"):
        self._token_client = token_client
        self._base_url = API_BASE_URLS[env]

    def request(
        self,
        method: str,
        path: str,
        scope: str,
        *,
        extra_headers: dict | None = None,
        **kwargs,
    ) -> httpx.Response:
        token = self._token_client.get_token(scope)
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Request-ID": str(uuid.uuid4()),
            "Content-Type": "application/json",
        }
        if extra_headers:
            headers.update(extra_headers)

        response = httpx.request(
            method,
            self._base_url + path,
            headers=headers,
            **kwargs,
        )
        if not response.is_success:
            raise APIError(response.status_code, response.text)
        return response

    def get(self, path: str, scope: str, **kwargs) -> httpx.Response:
        return self.request("GET", path, scope, **kwargs)

    def post(self, path: str, scope: str, **kwargs) -> httpx.Response:
        return self.request("POST", path, scope, **kwargs)
