from eltoque._config import ClientConfig
from eltoque._transport import USER_AGENT, build_request_parts

CONFIG = ClientConfig(api_token="fake.token")


def test_latest_request_has_no_query() -> None:
    url, params, headers = build_request_parts(CONFIG)
    assert url == "https://tasas.eltoque.com/v1/trmi"
    assert params == {}
    assert headers["Authorization"] == "Bearer fake.token"
    assert headers["Accept"] == "application/json"
    assert headers["User-Agent"] == USER_AGENT
    assert USER_AGENT.startswith("eltoque-python/")


def test_range_request_has_both_params() -> None:
    _, params, _ = build_request_parts(CONFIG, ("2022-10-27 00:00:00", "2022-10-27 23:59:59"))
    assert params == {"date_from": "2022-10-27 00:00:00", "date_to": "2022-10-27 23:59:59"}
