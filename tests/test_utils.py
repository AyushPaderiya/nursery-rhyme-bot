"""Tests for src/utils.py — shared pipeline utilities."""

import os
import json
from datetime import datetime
from unittest.mock import patch

import pytest

from src.utils import (
    load_env,
    ensure_dir,
    cleanup_files,
    get_today_category,
    get_today_length_tier,
    iso_now,
    retry,
)


# ---------------------------------------------------------------------------
# load_env
# ---------------------------------------------------------------------------
class TestLoadEnv:
    """Tests for environment variable loading."""

    def test_returns_value_when_set(self) -> None:
        """Should return the env var value when it exists."""
        with patch.dict("os.environ", {"TEST_KEY": "test_value"}):
            assert load_env("TEST_KEY") == "test_value"

    def test_raises_when_not_set(self) -> None:
        """Should raise ValueError with clear message when var is missing."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="TEST_KEY"):
                load_env("TEST_KEY")


# ---------------------------------------------------------------------------
# ensure_dir
# ---------------------------------------------------------------------------
class TestEnsureDir:
    """Tests for directory creation."""

    def test_creates_directory(self, tmp_path: str) -> None:
        """Should create directory if it doesn't exist."""
        target = os.path.join(str(tmp_path), "test_subdir")
        ensure_dir(target)
        assert os.path.isdir(target)

    def test_no_error_if_exists(self, tmp_path: str) -> None:
        """Should not raise if directory already exists."""
        target = os.path.join(str(tmp_path), "existing")
        os.makedirs(target)
        ensure_dir(target)  # should not raise


# ---------------------------------------------------------------------------
# cleanup_files
# ---------------------------------------------------------------------------
class TestCleanupFiles:
    """Tests for file cleanup."""

    def test_deletes_existing_files(self, tmp_path: str) -> None:
        """Should delete files that exist."""
        fpath = os.path.join(str(tmp_path), "delete_me.txt")
        with open(fpath, "w") as f:
            f.write("temp")
        cleanup_files([fpath])
        assert not os.path.exists(fpath)

    def test_skips_nonexistent_files(self) -> None:
        """Should silently skip files that don't exist."""
        cleanup_files(["/nonexistent/path/file.txt"])  # should not raise


# ---------------------------------------------------------------------------
# get_today_category
# ---------------------------------------------------------------------------
class TestGetTodayCategory:
    """Tests for 3-day content rotation."""

    def test_empty_tracker_returns_classic(self) -> None:
        """First ever run should return 'classic'."""
        assert get_today_category({"videos": []}) == "classic"

    def test_after_classic_returns_educational(self) -> None:
        """After classic, next should be educational."""
        tracker = {"videos": [{"category": "classic"}]}
        assert get_today_category(tracker) == "educational"

    def test_after_educational_returns_seasonal(self) -> None:
        """After educational, next should be seasonal."""
        tracker = {"videos": [{"category": "educational"}]}
        assert get_today_category(tracker) == "seasonal"

    def test_after_seasonal_returns_classic(self) -> None:
        """After seasonal, cycle restarts with classic."""
        tracker = {"videos": [{"category": "seasonal"}]}
        assert get_today_category(tracker) == "classic"

    def test_full_cycle(self) -> None:
        """Full rotation cycle should work correctly."""
        tracker: dict = {"videos": []}
        expected = ["classic", "educational", "seasonal", "classic"]
        for exp in expected:
            cat = get_today_category(tracker)
            assert cat == exp
            tracker["videos"].append({"category": cat})


# ---------------------------------------------------------------------------
# get_today_length_tier
# ---------------------------------------------------------------------------
class TestGetTodayLengthTier:
    """Tests for short/long alternation."""

    def test_empty_tracker_returns_short(self) -> None:
        """First ever run should return 'short'."""
        assert get_today_length_tier({"videos": []}) == "short"

    def test_after_short_returns_long(self) -> None:
        """After short, next should be long."""
        tracker = {"videos": [{"length_tier": "short"}]}
        assert get_today_length_tier(tracker) == "long"

    def test_after_long_returns_short(self) -> None:
        """After long, next should be short."""
        tracker = {"videos": [{"length_tier": "long"}]}
        assert get_today_length_tier(tracker) == "short"


# ---------------------------------------------------------------------------
# iso_now
# ---------------------------------------------------------------------------
class TestIsoNow:
    """Tests for ISO 8601 timestamp generation."""

    def test_returns_iso_string(self) -> None:
        """Should return a valid ISO 8601 formatted string."""
        result = iso_now()
        assert isinstance(result, str)
        # Should parse without error
        datetime.fromisoformat(result)

    def test_contains_utc_indicator(self) -> None:
        """Should contain UTC timezone info."""
        result = iso_now()
        assert "+" in result or "Z" in result


# ---------------------------------------------------------------------------
# retry decorator
# ---------------------------------------------------------------------------
class TestRetryDecorator:
    """Tests for the retry decorator."""

    def test_successful_function_not_retried(self) -> None:
        """A function that succeeds should only be called once."""
        call_count = 0

        @retry(max_attempts=3)
        def succeed() -> str:
            nonlocal call_count
            call_count += 1
            return "ok"

        result = succeed()
        assert result == "ok"
        assert call_count == 1

    @patch("src.alerting.send_telegram_alert", return_value=True)
    def test_alerts_on_final_failure(self, mock_alert) -> None:
        """Should send Telegram alert after all retries exhausted."""

        @retry(max_attempts=2, backoff_factor=0)
        def always_fail() -> None:
            raise RuntimeError("boom")

        with pytest.raises(RuntimeError, match="boom"):
            always_fail()

        mock_alert.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
