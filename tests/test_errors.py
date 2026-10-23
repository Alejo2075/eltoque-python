import pytest

from eltoque import exceptions as exc
from eltoque.models import RateLimitInfo

API_ERRORS = [
    exc.ElToqueBadRequestError,
    exc.ElToqueAuthenticationError,
    exc.ElToqueUnprocessableError,
    exc.ElToqueRateLimitError,
    exc.ElToqueServerError,
]
SIBLINGS = [
    exc.ElToqueConfigurationError,
    exc.ElToqueValidationError,
    exc.ElToqueNetworkError,
    exc.ElToqueTimeoutError,
    exc.ElToqueDecodeError,
    exc.ElToqueAPIError,
]


@pytest.mark.parametrize("cls", SIBLINGS)
def test_direct_children_of_base(cls: type[Exception]) -> None:
    assert cls.__bases__ == (exc.ElToqueError,)


@pytest.mark.parametrize("cls", API_ERRORS)
def test_api_errors_inherit_api_error(cls: type[exc.ElToqueAPIError]) -> None:
    assert issubclass(cls, exc.ElToqueAPIError)
    assert issubclass(cls, exc.ElToqueError)


def test_api_error_carries_metadata() -> None:
    info = RateLimitInfo(limit=60, remaining=0, retry_after=12.0)
    error = exc.ElToqueRateLimitError(
        "HTTP 429: rate limit exceeded", status_code=429, body_excerpt="slow down", rate_limit=info
    )
    assert error.status_code == 429
    assert error.body_excerpt == "slow down"
    assert error.rate_limit is info
    assert error.retry_after == 12.0
    assert str(error) == "HTTP 429: rate limit exceeded"


def test_explicit_retry_after_wins() -> None:
    error = exc.ElToqueRateLimitError(
        "x", status_code=429, rate_limit=RateLimitInfo(retry_after=1.0), retry_after=9.0
    )
    assert error.retry_after == 9.0


def test_defaults_are_none() -> None:
    error = exc.ElToqueServerError("boom", status_code=503)
    assert error.body_excerpt is None
    assert error.rate_limit is None
    assert error.retry_after is None
