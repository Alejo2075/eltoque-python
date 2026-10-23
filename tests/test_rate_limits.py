import httpx
import pytest

from eltoque.models import RateLimitInfo


def test_parses_integer_headers() -> None:
    info = RateLimitInfo.from_headers(
        {"X-RateLimit-Limit": "60", "X-RateLimit-Remaining": "59", "X-RateLimit-Reset": "1700"}
    )
    assert info == RateLimitInfo(limit=60, remaining=59, reset=1700, retry_after=None)


def test_header_names_are_case_insensitive() -> None:
    headers = httpx.Headers({"x-ratelimit-limit": "10", "RETRY-AFTER": "7"})
    info = RateLimitInfo.from_headers(headers)
    assert info.limit == 10
    assert info.retry_after == 7.0


def test_missing_headers_yield_none() -> None:
    assert RateLimitInfo.from_headers({}) == RateLimitInfo()


@pytest.mark.parametrize("value", ["abc", "", "-1", "1.5", "\uff11\uff12", "nan", " "])
def test_malformed_integers_are_ignored(value: str) -> None:
    info = RateLimitInfo.from_headers({"X-RateLimit-Limit": value, "X-RateLimit-Remaining": value})
    assert info.limit is None
    assert info.remaining is None


@pytest.mark.parametrize("value", ["soon", "-5", "nan", "inf", "Wed, 21 Oct 2026 07:28:00 GMT"])
def test_malformed_retry_after_is_ignored(value: str) -> None:
    assert RateLimitInfo.from_headers({"Retry-After": value}).retry_after is None


def test_retry_after_accepts_fractional_seconds() -> None:
    assert RateLimitInfo.from_headers({"Retry-After": "1.5"}).retry_after == 1.5
