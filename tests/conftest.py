import os
import pytest
from dotenv import load_dotenv

from luna_open_payments.auth import TokenClient
from luna_open_payments.client import OpenPaymentsClient
from luna_open_payments.aspsp import AspspService
from luna_open_payments.ais import AisService
from luna_open_payments.pis import PisService

load_dotenv()


@pytest.fixture(scope="session")
def env() -> str:
    return os.environ.get("OPEN_PAYMENTS_ENV", "sandbox")


@pytest.fixture(scope="session")
def token_client(env) -> TokenClient:
    client_id = os.environ["OPEN_PAYMENTS_CLIENT_ID"]
    client_secret = os.environ["OPEN_PAYMENTS_CLIENT_SECRET"]
    return TokenClient(client_id, client_secret, env)


@pytest.fixture(scope="session")
def client(token_client, env) -> OpenPaymentsClient:
    return OpenPaymentsClient(token_client, env)


@pytest.fixture(scope="session")
def aspsp_service(client) -> AspspService:
    return AspspService(client)


@pytest.fixture(scope="session")
def ais_service(client) -> AisService:
    return AisService(client)


@pytest.fixture(scope="session")
def pis_service(client) -> PisService:
    return PisService(client)


@pytest.fixture(scope="session")
def test_bic_fi(aspsp_service) -> str:
    """Return first available sandbox bank BIC."""
    aspsps = aspsp_service.list_aspsps()
    assert aspsps, "No ASPSPs returned from sandbox — check credentials"
    return aspsps[0].bicFi
