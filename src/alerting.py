"""Telegram alerting module for the Nursery Rhyme Bot pipeline.

Sends failure notifications to a Telegram chat via the Bot API so the
maintainer is informed when any pipeline step fails after all retries.
"""

import os
import sys
from typing import Optional

import requests

from src.utils import iso_now


def send_telegram_alert(message: str, traceback_str: str = "") -> None:
    """Send a plain-text alert message to Telegram.

    Uses TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID environment variables.
    Silently logs to stderr and returns if credentials are missing or
    the request fails (never crashes the pipeline).

    Args:
        message: The alert text to send.
        traceback_str: Optional traceback string to include.
    """
    bot_token: Optional[str] = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id: Optional[str] = os.environ.get("TELEGRAM_CHAT_ID")

    if not bot_token or not chat_id:
        print("[alerting] TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set — skipping alert.", file=sys.stderr)
        return

    repo = os.environ.get("GITHUB_REPOSITORY", "unknown/repo")
    run_id = os.environ.get("GITHUB_RUN_ID", "local")
    tb = traceback_str[:1000] if traceback_str else "None"

    text = (
        f"🚨 Nursery Rhyme Bot — PIPELINE FAILURE\n\n"
        f"Error: {message}\n\n"
        f"Traceback:\n{tb}\n\n"
        f"Time: {iso_now()}\n"
        f"Repo: {repo}\n"
        f"Run: {run_id}"
    )

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
    }

    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
    except Exception as exc:
        print(f"[alerting] Failed to send Telegram alert: {exc}", file=sys.stderr)


def send_success_notification(title: str, video_url: str, duration: float) -> None:
    """Send a success notification to Telegram.

    Args:
        title: The rhyme title.
        video_url: The YouTube video URL.
        duration: Duration of the video in seconds.
    """
    bot_token: Optional[str] = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id: Optional[str] = os.environ.get("TELEGRAM_CHAT_ID")

    if not bot_token or not chat_id:
        print("[alerting] TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set — skipping success notification.", file=sys.stderr)
        return

    text = (
        f"✅ New video uploaded!\n\n"
        f"Title: {title}\n"
        f"URL: {video_url}\n"
        f"Duration: {duration:.0f}s\n"
        f"Time: {iso_now()}"
    )

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
    }

    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
    except Exception as exc:
        print(f"[alerting] Failed to send Telegram success notification: {exc}", file=sys.stderr)


if __name__ == "__main__":
    send_telegram_alert("Test alert — pipeline scaffold verification.", "Test traceback")
    send_success_notification("Test Rhyme", "https://youtube.com/watch?v=123", 120.5)
    print("Test executed.")
