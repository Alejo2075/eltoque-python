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
