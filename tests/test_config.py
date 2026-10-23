import httpx
import pytest

from eltoque._config import MAX_RETRIES_LIMIT, ClientConfig
from eltoque.exceptions import ElToqueConfigurationError

TOKEN = "fake.jwt-token_123"


def test_valid_config_defaults() -> None:
    config = ClientConfig(api_token=TOKEN)
    assert config.max_retries == 0
    assert isinstance(config.timeout, httpx.Timeout)


@pytest.mark.parametrize(
    "token",
    [
        "",
        " ",
        "a b",
        "tok\r\nX-Evil: 1",
        "tok\n",
        "tok\x00",
        "Bearer abc",
        "tok\t",
        "tökén",
        None,
        5,
    ],
)
def test_invalid_tokens_rejected(token: object) -> None:
    with pytest.raises(ElToqueConfigurationError) as info:
        ClientConfig(api_token=token)  # type: ignore[arg-type]
    if isinstance(token, str) and token.strip():
        assert token not in str(info.value)


def test_repr_never_contains_token() -> None:
    config = ClientConfig(api_token=TOKEN)
    assert TOKEN not in repr(config)
    assert TOKEN not in str(config)
    assert "***" in repr(config)


def test_float_timeout_is_normalized() -> None:
    config = ClientConfig(api_token=TOKEN, timeout=3)
    assert config.timeout == httpx.Timeout(3.0)


def test_httpx_timeout_is_kept() -> None:
    timeout = httpx.Timeout(1.0, read=2.0)
    assert ClientConfig(api_token=TOKEN, timeout=timeout).timeout is timeout


@pytest.mark.parametrize("timeout", [0, -1, float("nan"), float("inf"), True, "5"])
def test_invalid_timeouts(timeout: object) -> None:
    with pytest.raises(ElToqueConfigurationError):
        ClientConfig(api_token=TOKEN, timeout=timeout)  # type: ignore[arg-type]


@pytest.mark.parametrize("retries", [-1, MAX_RETRIES_LIMIT + 1, 1.5, True, "2"])
def test_invalid_retries(retries: object) -> None:
    with pytest.raises(ElToqueConfigurationError):
        ClientConfig(api_token=TOKEN, max_retries=retries)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "field", ["max_retry_delay", "max_total_retry_delay", "max_response_bytes"]
)
def test_invalid_limits(field: str) -> None:
    with pytest.raises(ElToqueConfigurationError):
        ClientConfig(api_token=TOKEN, **{field: -1})  # type: ignore[arg-type]


def test_zero_response_limit_rejected() -> None:
    with pytest.raises(ElToqueConfigurationError):
        ClientConfig(api_token=TOKEN, max_response_bytes=0)


def test_default_base_url_is_official_https_origin() -> None:
    assert ClientConfig(api_token=TOKEN).base_url == "https://tasas.eltoque.com"


def test_trailing_slash_is_stripped() -> None:
    assert ClientConfig(api_token=TOKEN, base_url="https://example.test/").base_url == (
        "https://example.test"
    )


@pytest.mark.parametrize(
    "url", ["http://localhost:8000", "http://127.0.0.1:9999", "http://[::1]:8080"]
)
def test_plain_http_allowed_for_loopback(url: str) -> None:
    assert ClientConfig(api_token=TOKEN, base_url=url).base_url == url


@pytest.mark.parametrize(
    "url",
    [
        "http://tasas.eltoque.com",
        "ftp://example.test",
        "example.test",
        "https://",
        "",
        "https://user:pw@example.test",
        "https://example.test?x=1",
        "https://example.test#frag",
        "https://example.test:99999",
    ],
)
def test_unsafe_or_malformed_base_urls_rejected(url: str) -> None:
    with pytest.raises(ElToqueConfigurationError):
        ClientConfig(api_token=TOKEN, base_url=url)


def test_non_string_base_url_rejected() -> None:
    with pytest.raises(ElToqueConfigurationError):
        ClientConfig(api_token=TOKEN, base_url=None)  # type: ignore[arg-type]
