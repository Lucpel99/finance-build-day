import os
import pytest
from dotenv import load_dotenv
from zwapgrid import ZwapgridClient, ZwapgridError

load_dotenv()


@pytest.fixture(scope="session")
def zwapgrid_client() -> ZwapgridClient:
    api_key = os.environ.get("ZWAPGRID_API_KEY")
    consent_id = os.environ.get("ZWAPGRID_CONSENT_ID")
    if not api_key or not consent_id:
        pytest.skip("ZWAPGRID_API_KEY and ZWAPGRID_CONSENT_ID not set")
    return ZwapgridClient(api_key=api_key, consent_id=consent_id)


def test_get_company_information_returns_dict(zwapgrid_client: ZwapgridClient):
    result = zwapgrid_client.get_company_information()
    assert isinstance(result, dict)


def test_invalid_key_raises_zwapgrid_error():
    client = ZwapgridClient(api_key="invalid", consent_id="invalid")
    with pytest.raises(ZwapgridError) as exc_info:
        client.get_company_information()
    assert exc_info.value.status_code in (401, 403)
