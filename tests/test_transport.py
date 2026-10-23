import pytest

from eltoque import exceptions as exc
from eltoque._config import ClientConfig
from eltoque._transport import USER_AGENT, build_request_parts, error_for_response, make_excerpt

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


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (400, exc.ElToqueBadRequestError),
        (401, exc.ElToqueAuthenticationError),
        (422, exc.ElToqueUnprocessableError),
        (429, exc.ElToqueRateLimitError),
        (500, exc.ElToqueServerError),
        (503, exc.ElToqueServerError),
        (599, exc.ElToqueServerError),
        (301, exc.ElToqueAPIError),
        (302, exc.ElToqueAPIError),
        (403, exc.ElToqueAPIError),
        (404, exc.ElToqueAPIError),
    ],
)
def test_status_mapping(status: int, expected: type[exc.ElToqueAPIError]) -> None:
    error = error_for_response(status, {}, b"", "tok")
    assert error is not None
    assert type(error) is expected
    assert error.status_code == status
    assert str(error).startswith(f"HTTP {status}")


@pytest.mark.parametrize("status", [200, 201, 204, 299])
def test_success_statuses_have_no_error(status: int) -> None:
    assert error_for_response(status, {}, b"", "tok") is None


def test_429_carries_retry_after_and_rate_limit() -> None:
    headers = {"Retry-After": "30", "X-RateLimit-Limit": "60", "X-RateLimit-Remaining": "0"}
    error = error_for_response(429, headers, b'{"error": "slow"}', "tok")
    assert error is not None
    assert error.retry_after == 30.0
    assert error.rate_limit is not None
    assert error.rate_limit.remaining == 0
    assert error.body_excerpt == '{"error": "slow"}'


def test_body_is_never_in_message() -> None:
    error = error_for_response(500, {}, b"secret provider body", "tok")
    assert error is not None
    assert "secret provider body" not in str(error)


def test_excerpt_redacts_token_truncates_and_strips_control_chars() -> None:
    assert make_excerpt(b"echo tok123 here", "tok123") == "echo *** here"
    assert make_excerpt(b"a\r\nb\x00c", "t") == "a b c"
    long = make_excerpt(b"x" * 1000, "t")
    assert long is not None
    assert len(long) == 203
    assert long.endswith("...")
    assert make_excerpt(b"", "t") is None
    assert make_excerpt(b" \n ", "t") is None
    assert make_excerpt(b"\xff\xfe", "t") is not None
