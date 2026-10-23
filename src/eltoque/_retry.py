"""Pure retry policy shared by the sync and async clients (internal). It never sleeps."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from eltoque.exceptions import (
    ElToqueAPIError,
    ElToqueNetworkError,
    ElToqueRateLimitError,
    ElToqueTimeoutError,
)

if TYPE_CHECKING:
    from eltoque._config import ClientConfig
    from eltoque.exceptions import ElToqueError

TRANSIENT_STATUSES = frozenset({502, 503, 504})
BACKOFF_BASE = 0.5


@dataclass(slots=True)
class RetryPolicy:
    """Decides whether and how long to wait before the next attempt.

    Retries are opt-in (``max_retries=0`` by default) and consume API quota. A request is
    retried only for 429, transient gateway statuses (502/503/504) and transport failures.
    400/401/422 are never retried. If the server asks for a wait longer than
    ``max_retry_delay`` (or the total budget), the error is raised instead.
    """

    max_retries: int
    max_delay: float
    max_total_delay: float
    retries_done: int = 0
    total_delay: float = 0.0

    @classmethod
    def from_config(cls, config: ClientConfig) -> RetryPolicy:
        return cls(config.max_retries, config.max_retry_delay, config.max_total_retry_delay)

    @staticmethod
    def is_retryable(error: ElToqueError) -> bool:
        if isinstance(error, ElToqueRateLimitError | ElToqueNetworkError | ElToqueTimeoutError):
            return True
        return isinstance(error, ElToqueAPIError) and error.status_code in TRANSIENT_STATUSES

    def next_delay(self, error: ElToqueError) -> float | None:
        """Return seconds to wait before retrying, or ``None`` to give up and raise."""
        if self.retries_done >= self.max_retries or not self.is_retryable(error):
            return None
        retry_after = error.retry_after if isinstance(error, ElToqueAPIError) else None
        delay = retry_after if retry_after is not None else BACKOFF_BASE * 2**self.retries_done
        if delay > self.max_delay or self.total_delay + delay > self.max_total_delay:
            return None
        self.retries_done += 1
        self.total_delay += delay
        return delay
