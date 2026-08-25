import time
import httpx

AUTH_URLS = {
    "sandbox": "https://auth.sandbox.openbankingplatform.com/connect/token",
    "production": "https://auth.openbankingplatform.com/connect/token",
}


class AuthError(Exception):
    def __init__(self, status_code: int, body: str):
        super().__init__(f"Token request failed [{status_code}]: {body}")
        self.status_code = status_code
        self.body = body


class TokenClient:
    def __init__(self, client_id: str, client_secret: str, env: str = "sandbox"):
        self._client_id = client_id
        self._client_secret = client_secret
        self._token_url = AUTH_URLS[env]
        # cache: scope -> (access_token, expires_at)
        self._cache: dict[str, tuple[str, float]] = {}

    def get_token(self, scope: str) -> str:
        now = time.monotonic()
        cached = self._cache.get(scope)
        if cached and cached[1] > now + 60:
            return cached[0]

        response = httpx.post(
            self._token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "scope": scope,
            },
        )
        if response.status_code != 200:
            raise AuthError(response.status_code, response.text)

        payload = response.json()
        token = payload["access_token"]
        expires_in = int(payload.get("expires_in", 3600))
        self._cache[scope] = (token, now + expires_in)
        return token
