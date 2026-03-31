"""Tests for src/alerting.py."""

from unittest.mock import patch, MagicMock

import pytest

from src.alerting import send_telegram_alert, send_success_notification


class TestSendTelegramAlert:
    """Tests for Telegram alert sending."""

    def test_returns_none_without_credentials(self) -> None:
        """Should log and return when TELEGRAM env vars are not set."""
        with patch.dict("os.environ", {}, clear=True):
            result = send_telegram_alert("test message", "tb")
            assert result is None

    @patch("src.alerting.requests.post")
    @patch("src.alerting.iso_now", return_value="2024-01-01T00:00:00Z")
    def test_sends_alert_with_credentials(self, mock_iso: MagicMock, mock_post: MagicMock) -> None:
        """Should POST to Telegram API when credentials are available."""
        mock_post.return_value = MagicMock(status_code=200)
        mock_post.return_value.raise_for_status = MagicMock()

        with patch.dict(
            "os.environ",
            {
                "TELEGRAM_BOT_TOKEN": "fake-token", 
                "TELEGRAM_CHAT_ID": "12345",
                "GITHUB_REPOSITORY": "test/repo",
                "GITHUB_RUN_ID": "999"
            },
        ):
            result = send_telegram_alert("test alert", "test error")
            assert result is None
            mock_post.assert_called_once()
            
            # Verify payload logic
            payload = mock_post.call_args[1]["json"]
            assert "test alert" in payload["text"]
            assert "test error" in payload["text"]
            assert "test/repo" in payload["text"]
            assert "999" in payload["text"]

    @patch("src.alerting.requests.post")
    def test_returns_none_on_request_error(self, mock_post: MagicMock) -> None:
        """Should return None without crashing when the HTTP request fails."""
        import requests as req

        mock_post.side_effect = req.RequestException("Network error")

        with patch.dict(
            "os.environ",
            {"TELEGRAM_BOT_TOKEN": "fake-token", "TELEGRAM_CHAT_ID": "12345"},
        ):
            # If it crashed, it would raise an exception here
            result = send_telegram_alert("test alert")
            assert result is None


class TestSendSuccessNotification:
    """Tests for Telegram success notifications."""

    def test_returns_none_without_credentials(self) -> None:
        """Should log and return when TELEGRAM env vars are not set."""
        with patch.dict("os.environ", {}, clear=True):
            result = send_success_notification("Test Title", "http://yt.be", 120.0)
            assert result is None

    @patch("src.alerting.requests.post")
    def test_sends_success_with_credentials(self, mock_post: MagicMock) -> None:
        """Should POST to Telegram API when credentials are available."""
        mock_post.return_value = MagicMock(status_code=200)
        mock_post.return_value.raise_for_status = MagicMock()

        with patch.dict(
            "os.environ",
            {"TELEGRAM_BOT_TOKEN": "fake-token", "TELEGRAM_CHAT_ID": "12345"},
        ):
            result = send_success_notification("Test Title", "http://yt.be", 120.0)
            assert result is None
            mock_post.assert_called_once()
            
            payload = mock_post.call_args[1]["json"]
            assert "Test Title" in payload["text"]
            assert "http://yt.be" in payload["text"]
            assert "120s" in payload["text"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
