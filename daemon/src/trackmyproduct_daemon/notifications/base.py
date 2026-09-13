"""Pluggable notification channel interface.

Only Telegram is implemented for real (per task scope). Rakazo and Grok Bot
are named as future channels in docs/product-brief.md but are not required
now — a future channel just implements :class:`NotificationChannel` and
gets registered alongside Telegram in ``scan.py``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class Notification:
    key: str  # dedupe key: "ath:<listing_id>" | "atl:<listing_id>" | "cross-platform:<platform>:<date>"
    text: str


class NotificationChannel(Protocol):
    def send(self, notification: Notification) -> bool:
        """Send a notification. Returns True on success."""
        ...
