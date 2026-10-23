import json
from datetime import datetime

import httpx
import pytest

from eltoque import exceptions as exc
from eltoque._client import ElToqueClient
from tests.conftest import TOKEN, Recorder, json_response


def make(recorder: Recorder, **kwargs: object) -> ElToqueClient:
    return ElToqueClient(TOKEN, transport=httpx.MockTransport(recorder), **kwargs)  # type: ignore[arg-type]


def test_latest_rates_request_shape() -> None:
    recorder = Recorder(json_response({"any": "shape"}))
    response = make(recorder).get_latest_rates()
    request = recorder.requests[0]
    assert request.method == "GET"
    assert str(request.url) == "https://tasas.eltoque.com/v1/trmi"
    assert request.headers["Authorization"] == f"Bearer {TOKEN}"
    assert request.headers["Accept"] == "application/json"
    assert request.headers["User-Agent"].startswith("eltoque-python/")
    assert response.data == {"any": "shape"}
    assert response.status_code == 200


def test_ranged_rates_query_encoding() -> None:
    recorder = Recorder(json_response([1, 2]))
    response = make(recorder).get_rates(
        datetime(2022, 10, 27, 0, 0, 0), datetime(2022, 10, 27, 23, 59, 59)
    )
    request = recorder.requests[0]
    assert request.url.params["date_from"] == "2022-10-27 00:00:00"
    assert request.url.params["date_to"] == "2022-10-27 23:59:59"
    assert response.data == [1, 2]


def test_invalid_range_fails_before_any_request() -> None:
    recorder = Recorder(json_response())
    client = make(recorder)
    with pytest.raises(exc.ElToqueValidationError):
        client.get_rates(datetime(2022, 10, 27), datetime(2022, 10, 28))
    assert recorder.requests == []


def test_rate_limit_metadata_exposed() -> None:
    recorder = Recorder(json_response(**{"X-RateLimit-Limit": "60", "X-RateLimit-Remaining": "59"}))
    response = make(recorder).get_latest_rates()
    assert response.rate_limit.limit == 60
    assert response.rate_limit.remaining == 59
    assert response.rate_limit.reset is None


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (400, exc.ElToqueBadRequestError),
        (401, exc.ElToqueAuthenticationError),
        (422, exc.ElToqueUnprocessableError),
        (429, exc.ElToqueRateLimitError),
        (500, exc.ElToqueServerError),
        (404, exc.ElToqueAPIError),
    ],
)
def test_error_statuses_raise(status: int, expected: type[exc.ElToqueAPIError]) -> None:
    recorder = Recorder(httpx.Response(status, json={"error": "nope"}))
    with pytest.raises(expected) as info:
        make(recorder).get_latest_rates()
    assert info.value.status_code == status
    assert TOKEN not in str(info.value)


def test_429_exposes_retry_after() -> None:
    recorder = Recorder(
        httpx.Response(
            429, json={"error": "x", "limit": "60 per 1 minute"}, headers={"Retry-After": "12"}
        )
    )
    with pytest.raises(exc.ElToqueRateLimitError) as info:
        make(recorder).get_latest_rates()
    assert info.value.retry_after == 12.0


@pytest.mark.parametrize("body", [b"", b"<html>", b"{bad"])
def test_invalid_success_body_raises_decode_error(body: bytes) -> None:
    with pytest.raises(exc.ElToqueDecodeError):
        make(Recorder(httpx.Response(200, content=body))).get_latest_rates()


@pytest.mark.parametrize("payload", [None, 0, "x", [], {}])
def test_any_json_value_is_returned_untouched(payload: object) -> None:
    response = make(Recorder(httpx.Response(200, content=json.dumps(payload)))).get_latest_rates()
    assert response.data == payload


def test_transport_failures_are_translated() -> None:
    with pytest.raises(exc.ElToqueTimeoutError):
        make(Recorder(httpx.ReadTimeout("slow"))).get_latest_rates()
    with pytest.raises(exc.ElToqueNetworkError):
        make(Recorder(httpx.ConnectError("down"))).get_latest_rates()


def test_redirect_is_not_followed() -> None:
    recorder = Recorder(httpx.Response(302, headers={"Location": "https://evil.test/v1/trmi"}))
    with pytest.raises(exc.ElToqueAPIError) as info:
        make(recorder).get_latest_rates()
    assert info.value.status_code == 302
    assert len(recorder.requests) == 1


def test_oversized_success_body_rejected() -> None:
    recorder = Recorder(httpx.Response(200, content=b"[" + b"1," * 3_000_000 + b"1]"))
    with pytest.raises(exc.ElToqueDecodeError, match="limit"):
        make(recorder).get_latest_rates()


def test_repr_has_no_token() -> None:
    assert TOKEN not in repr(make(Recorder(json_response())))


def test_invalid_token_rejected_at_construction() -> None:
    with pytest.raises(exc.ElToqueConfigurationError):
        ElToqueClient("bad token")


def test_context_manager_closes_client() -> None:
    recorder = Recorder(json_response())
    with make(recorder) as client:
        client.get_latest_rates()
    with pytest.raises(exc.ElToqueError, match="closed"):
        client.get_latest_rates()
    assert len(recorder.requests) == 1


def test_close_is_idempotent() -> None:
    client = make(Recorder(json_response()))
    client.close()
    client.close()


def test_cannot_reenter_closed_client() -> None:
    client = make(Recorder(json_response()))
    client.close()
    with pytest.raises(exc.ElToqueError, match="closed"), client:
        pass


def test_closed_client_validates_nothing_and_sends_nothing() -> None:
    recorder = Recorder(json_response())
    client = make(recorder)
    client.close()
    with pytest.raises(exc.ElToqueError, match="closed"):
        client.get_rates(datetime(2022, 10, 27), datetime(2022, 10, 27, 1))
    assert recorder.requests == []


def test_injected_http_client_is_used_and_not_closed() -> None:
    recorder = Recorder(json_response())
    http = httpx.Client(transport=httpx.MockTransport(recorder))
    with ElToqueClient(TOKEN, http_client=http) as client:
        client.get_latest_rates()
    assert len(recorder.requests) == 1
    assert not http.is_closed
    http.close()


def test_owned_http_client_is_closed() -> None:
    client = make(Recorder(json_response()))
    client.close()
    assert client._http.is_closed


def test_injected_client_cannot_make_sdk_follow_redirects() -> None:
    recorder = Recorder(httpx.Response(307, headers={"Location": "https://evil.test/"}))
    http = httpx.Client(transport=httpx.MockTransport(recorder), follow_redirects=True)
    with pytest.raises(exc.ElToqueAPIError) as info:
        ElToqueClient(TOKEN, http_client=http).get_latest_rates()
    assert info.value.status_code == 307
    assert len(recorder.requests) == 1
    http.close()


def test_http_client_and_transport_are_mutually_exclusive() -> None:
    http = httpx.Client()
    with pytest.raises(exc.ElToqueConfigurationError):
        ElToqueClient(TOKEN, http_client=http, transport=httpx.MockTransport(Recorder()))
    http.close()
