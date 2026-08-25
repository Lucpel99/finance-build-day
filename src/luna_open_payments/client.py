import uuid

import httpx

from .auth import TokenClient


_ENV_BASE_URLS = {
    "sandbox": "https://api.sandbox.openbankingplatform.com",
    "production": "https://api.openbankingplatform.com",
}


class APIError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(
            f"API error [{status_code}]: {message}"
        )


class OpenPaymentsClient:
    def __init__(
        self,
        token_client: TokenClient,
        *,
        env: str = "sandbox",
        timeout: float = 30.0,
    ):
        self._token_client = token_client
        self._base_url = _ENV_BASE_URLS[env]
        self._http = httpx.Client(
            timeout=timeout
        )

    def request(
        self,
        method: str,
        path: str,
        scope: str,
        *,
        extra_headers: dict | None = None,
        **kwargs,
    ) -> httpx.Response:

        # Get OAuth token
        access_token = self._token_client.get_token(scope)

        headers = {
            "Authorization": f"Bearer {access_token}",
            "X-Request-ID": str(uuid.uuid4()),
            "Accept": "application/json",
        }

        if extra_headers:
            headers.update(extra_headers)

        response = self._http.request(
            method=method,
            url=f"{self._base_url}{path}",
            headers=headers,
            **kwargs,
        )

        if not response.is_success:
            raise APIError(
                response.status_code,
                response.text,
            )

        return response

    def get(
        self,
        path: str,
        scope: str,
        **kwargs,
    ) -> httpx.Response:

        return self.request(
            "GET",
            path,
            scope,
            **kwargs,
        )

    def post(
        self,
        path: str,
        scope: str,
        **kwargs,
    ) -> httpx.Response:

        return self.request(
            "POST",
            path,
            scope,
            **kwargs,
        )

    def put(
        self,
        path: str,
        scope: str,
        **kwargs,
    ) -> httpx.Response:

        return self.request(
            "PUT",
            path,
            scope,
            **kwargs,
        )