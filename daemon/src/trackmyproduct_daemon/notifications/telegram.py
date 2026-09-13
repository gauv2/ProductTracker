"""Telegram notification channel — real implementation.

Uses the plain Telegram Bot HTTP API directly (no SDK dependency needed for
one call). Setup (documented again in README):

1. Message ``@BotFather`` on Telegram, run ``/newbot``, copy the token it
   gives you into the daemon config as ``telegram_bot_token``.
2. Send any message to your new bot, then hit
   ``https://api.telegram.org/bot<token>/getUpdates`` to find your numeric
   chat id, and put it in ``telegram_chat_id``.
"""

from __future__ import annotations

import logging

import httpx

from .base import Notification

logger = logging.getLogger(__name__)

API_BASE = "https://api.telegram.org"


class TelegramChannel:
    def __init__(self, bot_token: str, chat_id: str, timeout: float = 10.0):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.timeout = timeout

    def send(self, notification: Notification) -> bool:
        if not self.bot_token or not self.chat_id:
            logger.warning(
                "telegram channel not configured (telegram_bot_token / "
                "telegram_chat_id) — dropping notification %s",
                notification.key,
            )
            return False

        url = f"{API_BASE}/bot{self.bot_token}/sendMessage"
        try:
            response = httpx.post(
                url,
                json={"chat_id": self.chat_id, "text": notification.text},
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError):
            logger.warning("telegram send failed for %s", notification.key, exc_info=True)
            return False

        if not payload.get("ok"):
            logger.warning("telegram API rejected message for %s: %s", notification.key, payload)
            return False
        return True
