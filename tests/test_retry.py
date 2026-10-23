import pytest

from eltoque import exceptions as exc
from eltoque._config import ClientConfig
from eltoque._retry import RetryPolicy
from eltoque.models import RateLimitInfo


def policy(retries: int = 3, delay: float = 30.0, total: float = 60.0) -> RetryPolicy:
    return RetryPolicy(retries, delay, total)


def api(cls: type[exc.ElToqueAPIError], status: int, retry_after: float | None = None):
    info = RateLimitInfo(retry_after=retry_after)
    return cls("x", status_code=status, rate_limit=info)


def test_disabled_by_default() -> None:
    p = RetryPolicy.from_config(ClientConfig(api_token="t"))
    assert p.next_delay(api(exc.ElToqueRateLimitError, 429, 1)) is None


@pytest.mark.parametrize(
    "error",
    [
        api(exc.ElToqueBadRequestError, 400),
        api(exc.ElToqueAuthenticationError, 401),
        api(exc.ElToqueUnprocessableError, 422),
        api(exc.ElToqueServerError, 500),
        api(exc.ElToqueAPIError, 404),
        exc.ElToqueDecodeError("x"),
        exc.ElToqueValidationError("x"),
    ],
)
def test_non_retryable(error: exc.ElToqueError) -> None:
    assert policy().next_delay(error) is None


@pytest.mark.parametrize(
    "error",
    [
        api(exc.ElToqueServerError, 502),
        api(exc.ElToqueServerError, 503),
        api(exc.ElToqueServerError, 504),
        exc.ElToqueNetworkError("x"),
        exc.ElToqueTimeoutError("x"),
    ],
)
def test_retryable_uses_exponential_backoff(error: exc.ElToqueError) -> None:
    p = policy()
    assert [p.next_delay(error) for _ in range(4)] == [0.5, 1.0, 2.0, None]


def test_retry_after_is_honored() -> None:
    p = policy()
    assert p.next_delay(api(exc.ElToqueRateLimitError, 429, 7)) == 7


def test_429_without_retry_after_falls_back_to_backoff() -> None:
    assert policy().next_delay(api(exc.ElToqueRateLimitError, 429)) == 0.5


def test_retry_after_longer_than_cap_gives_up() -> None:
    assert policy(delay=10).next_delay(api(exc.ElToqueRateLimitError, 429, 11)) is None


def test_total_budget_is_enforced() -> None:
    p = policy(retries=5, delay=30, total=50)
    error = api(exc.ElToqueRateLimitError, 429, 30)
    assert p.next_delay(error) == 30
    assert p.next_delay(error) is None  # 60 > 50


def test_attempt_count_is_capped() -> None:
    p = policy(retries=2)
    error = exc.ElToqueNetworkError("x")
    assert p.next_delay(error) is not None
    assert p.next_delay(error) is not None
    assert p.next_delay(error) is None
    assert p.retries_done == 2
