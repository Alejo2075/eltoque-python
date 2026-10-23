"""Unofficial, typed Python client for the official elTOQUE exchange-rate API.

Exchange rates are indicative, not official. Source: elTOQUE.
Access requires registration and an application-specific API token.
"""

from eltoque._client import ElToqueClient
from eltoque._version import __version__
from eltoque.exceptions import (
    ElToqueAPIError,
    ElToqueAuthenticationError,
    ElToqueBadRequestError,
    ElToqueConfigurationError,
    ElToqueDecodeError,
    ElToqueError,
    ElToqueNetworkError,
    ElToqueRateLimitError,
    ElToqueServerError,
    ElToqueTimeoutError,
    ElToqueUnprocessableError,
    ElToqueValidationError,
)
from eltoque.models import RateLimitInfo, RatesResponse

__all__ = [
    "ElToqueAPIError",
    "ElToqueAuthenticationError",
    "ElToqueBadRequestError",
    "ElToqueClient",
    "ElToqueConfigurationError",
    "ElToqueDecodeError",
    "ElToqueError",
    "ElToqueNetworkError",
    "ElToqueRateLimitError",
    "ElToqueServerError",
    "ElToqueTimeoutError",
    "ElToqueUnprocessableError",
    "ElToqueValidationError",
    "RateLimitInfo",
    "RatesResponse",
    "__version__",
]
