"""Shared utility functions for the Nursery Rhyme Bot pipeline.

Provides retry decorator with Telegram alerting on final failure,
environment variable loading, directory management, file cleanup,
content rotation helpers, and timestamp utilities.
"""

import os
import json
from datetime import datetime, timezone
from typing import Any, Callable, TypeVar
from functools import wraps

from tenacity import (
    retry as tenacity_retry,
    stop_after_attempt,
    wait_exponential,
    RetryError,
)

F = TypeVar("F", bound=Callable[..., Any])

# ---------------------------------------------------------------------------
# 3-day category rotation order
# ---------------------------------------------------------------------------
_CATEGORY_ROTATION: list[str] = ["classic", "educational", "seasonal"]

# ---------------------------------------------------------------------------
# Retry decorator
# ---------------------------------------------------------------------------


def retry(max_attempts: int = 3, backoff_factor: int = 2) -> Callable[[F], F]:
    """Decorator that retries a function with exponential back-off.

    On final failure the error is forwarded to `alerting.send_telegram_alert`
    (imported lazily to avoid circular imports) and then re-raised.

    Args:
        max_attempts: Maximum number of attempts before giving up.
        backoff_factor: Multiplier for exponential back-off between retries.

    Returns:
        Decorated function with retry behaviour.
    """

    def decorator(func: F) -> F:
        @tenacity_retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=backoff_factor, min=1, max=60),
            reraise=True,
        )
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

        @wraps(func)
        def outer(*args: Any, **kwargs: Any) -> Any:
            try:
                return wrapper(*args, **kwargs)
            except Exception as exc:
                # Lazy import to avoid circular dependency
                from src.alerting import send_telegram_alert

                send_telegram_alert(
                    f"[{func.__name__}] failed after {max_attempts} attempts: {exc}"
                )
                raise

        return outer  # type: ignore[return-value]

    return decorator


# ---------------------------------------------------------------------------
# Environment helpers
# ---------------------------------------------------------------------------


def load_env(key: str) -> str:
    """Read an environment variable or raise with a clear message.

    Args:
        key: Name of the environment variable.

    Returns:
        The value of the environment variable.

    Raises:
        ValueError: If the environment variable is not set.
    """
    value = os.environ.get(key)
    if value is None:
        raise ValueError(
            f"Required environment variable '{key}' is not set. "
            f"Add it to your .env or GitHub Secrets."
        )
    return value


# ---------------------------------------------------------------------------
# File-system helpers
# ---------------------------------------------------------------------------


def ensure_dir(path: str) -> None:
    """Create a directory (and parents) if it does not already exist.

    Args:
        path: Directory path to create.
    """
    os.makedirs(path, exist_ok=True)


def cleanup_files(paths: list[str]) -> None:
    """Delete a list of files, silently skipping any that don't exist.

    Args:
        paths: List of file paths to remove.
    """
    for p in paths:
        try:
            os.remove(p)
        except FileNotFoundError:
            pass


# ---------------------------------------------------------------------------
# Content rotation helpers
# ---------------------------------------------------------------------------


def get_today_category(tracker: dict) -> str:
    """Determine today's content category based on the 3-day rotation.

    Reads the last entry in the tracker's ``videos`` list and returns the
    next category in the cycle: classic → educational → seasonal → classic …

    Args:
        tracker: Parsed content_tracker.json dict with a ``videos`` key.

    Returns:
        One of ``"classic"``, ``"educational"``, or ``"seasonal"``.
    """
    videos = tracker.get("videos", [])
    if not videos:
        return _CATEGORY_ROTATION[0]

    last_category = videos[-1].get("category", "seasonal")
    try:
        idx = _CATEGORY_ROTATION.index(last_category)
    except ValueError:
        return _CATEGORY_ROTATION[0]

    return _CATEGORY_ROTATION[(idx + 1) % len(_CATEGORY_ROTATION)]


def get_today_length_tier(tracker: dict) -> str:
    """Determine today's video length tier by alternating short ↔ long.

    Args:
        tracker: Parsed content_tracker.json dict with a ``videos`` key.

    Returns:
        ``"short"`` or ``"long"``.
    """
    videos = tracker.get("videos", [])
    if not videos:
        return "short"

    last_tier = videos[-1].get("length_tier", "long")
    return "long" if last_tier == "short" else "short"


# ---------------------------------------------------------------------------
# Timestamp helper
# ---------------------------------------------------------------------------


def iso_now() -> str:
    """Return the current UTC time as an ISO 8601 string.

    Returns:
        ISO 8601 formatted UTC timestamp string.
    """
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Entry point for quick smoke-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print(f"iso_now          → {iso_now()}")
    print(f"get_today_category (empty) → {get_today_category({'videos': []})}")
    print(f"get_today_length_tier (empty) → {get_today_length_tier({'videos': []})}")
    print("utils.py — all functions defined ✓")
