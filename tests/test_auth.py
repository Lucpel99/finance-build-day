import time
from luna_open_payments.auth import TokenClient


def test_token_returned(token_client: TokenClient):
    token = token_client.get_token("aspspinformation private")
    assert isinstance(token, str)
    assert len(token) > 20


def test_token_cached(token_client: TokenClient):
    t1 = token_client.get_token("aspspinformation private")
    t2 = token_client.get_token("aspspinformation private")
    assert t1 == t2, "Second call should return cached token"


def test_different_scopes_independent(token_client: TokenClient):
    t1 = token_client.get_token("aspspinformation private")
    t2 = token_client.get_token("accountinformation private")
    # Both should be non-empty strings (may or may not be equal depending on server)
    assert t1 and t2
