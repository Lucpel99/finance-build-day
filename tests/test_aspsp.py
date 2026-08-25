from luna_open_payments.aspsp import AspspService
from luna_open_payments.models import Aspsp, Country


def test_list_aspsps_returns_results(aspsp_service: AspspService):
    aspsps = aspsp_service.list_aspsps()
    assert len(aspsps) > 0


def test_aspsp_has_required_fields(aspsp_service: AspspService):
    aspsps = aspsp_service.list_aspsps()
    for aspsp in aspsps[:5]:
        assert isinstance(aspsp, Aspsp)
        assert aspsp.bicFi
        assert aspsp.name


def test_get_aspsp_by_bic(aspsp_service: AspspService, test_bic_fi: str):
    aspsp = aspsp_service.get_aspsp(test_bic_fi)
    assert isinstance(aspsp, Aspsp)
    assert aspsp.bicFi == test_bic_fi


def test_list_countries(aspsp_service: AspspService):
    countries = aspsp_service.list_countries()
    assert len(countries) > 0
    for country in countries:
        assert isinstance(country, Country)
        assert country.isoCountryCode
