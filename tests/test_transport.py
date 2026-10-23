from collections.abc import AsyncIterator

import httpx
import pytest

from eltoque import exceptions as exc
from eltoque._config import ClientConfig
from eltoque._transport import (
    USER_AGENT,
    aread_limited,
    build_request_parts,
    check_declared_length,
    decode_json,
    error_for_response,
    make_excerpt,
    read_limited,
)

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


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        (b'{"a": 1}', {"a": 1}),
        (b"[1, 2]", [1, 2]),
        (b'"text"', "text"),
        (b"12.50", 12.5),
        (b"null", None),
        (b"true", True),
        (b"  [] \n", []),
    ],
)
def test_decode_json_preserves_any_json_value(body: bytes, expected: object) -> None:
    assert decode_json(body) == expected


@pytest.mark.parametrize("body", [b"", b"  \n", b"<html>", b"{bad", b"\xff\xfe\x00"])
def test_decode_json_rejects_garbage(body: bytes) -> None:
    with pytest.raises(exc.ElToqueDecodeError):
        decode_json(body)


def _streamed(body: bytes, headers: dict[str, str] | None = None) -> httpx.Response:
    return httpx.Response(
        200, content=iter([body[i : i + 4] for i in range(0, len(body), 4)]), headers=headers
    )


def test_read_limited_returns_full_body_under_limit() -> None:
    assert read_limited(_streamed(b"0123456789"), 10) == b"0123456789"


def test_read_limited_strict_raises_over_limit() -> None:
    with pytest.raises(exc.ElToqueDecodeError, match="limit"):
        read_limited(_streamed(b"0123456789A"), 10)


def test_read_limited_non_strict_truncates() -> None:
    assert read_limited(_streamed(b"0123456789ABCDEF"), 10, strict=False) == b"0123456789"


def test_declared_content_length_rejected_before_reading() -> None:
    response = httpx.Response(200, content=b"x", headers={"content-length": "999"})
    # httpx recomputes nothing here: header is explicit, so the early check must trigger.
    with pytest.raises(exc.ElToqueDecodeError):
        check_declared_length(response.headers, 10, strict=True)
    check_declared_length(response.headers, 10, strict=False)


async def test_aread_limited_matches_sync_behaviour() -> None:
    async def gen() -> AsyncIterator[bytes]:
        for chunk in (b"0123", b"4567", b"89AB"):
            yield chunk

    assert await aread_limited(httpx.Response(200, content=gen()), 12) == b"0123456789AB"
    with pytest.raises(exc.ElToqueDecodeError):
        await aread_limited(httpx.Response(200, content=gen()), 10)
    assert (
        await aread_limited(httpx.Response(200, content=gen()), 10, strict=False) == b"0123456789"
    )
