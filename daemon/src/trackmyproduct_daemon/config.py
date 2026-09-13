"""Daemon configuration.

Loaded from a JSON file (default: ``~/.trackmyproduct/config.json``), with
every field overridable by an environment variable of the same name
upper-cased and prefixed with ``TMP_`` (e.g. ``TMP_VAULT_PATH``). Secrets
(Telegram bot token, eBay app credentials) are only ever read from the
environment or the config file on disk — never hardcoded.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any

DEFAULT_CONFIG_PATH = Path.home() / ".trackmyproduct" / "config.json"


@dataclass
class Config:
    # Vault
    vault_path: str = str(Path.home() / "TrackMyProduct")

    # API server
    host: str = "127.0.0.1"
    port: int = 8756

    # Scheduler
    scan_interval_minutes: int = 15

    # Telegram
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # eBay Browse API (see README for setup)
    ebay_client_id: str = ""
    ebay_client_secret: str = ""
    ebay_marketplace_id: str = "EBAY_NL"

    # Facebook Marketplace (best-effort; see README)
    facebook_cookie: str = ""
    facebook_locale: str = "nl_NL"

    # Tweakers Pricewatch (best-effort; see README)
    tweakers_cookie: str = ""

    # Google Custom Search (used for "new price" lookup; see README)
    google_api_key: str = ""
    google_cse_id: str = ""

    # Marktplaats
    marktplaats_base_url: str = "https://www.marktplaats.nl"

    @property
    def vault_dir(self) -> Path:
        return Path(self.vault_path).expanduser()

    @classmethod
    def load(cls, path: Path | None = None) -> "Config":
        path = path or Path(os.environ.get("TMP_CONFIG_PATH", DEFAULT_CONFIG_PATH))
        data: dict[str, Any] = {}
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))

        known = {f.name for f in fields(cls)}
        data = {k: v for k, v in data.items() if k in known}

        int_fields = {"port", "scan_interval_minutes"}
        for f in fields(cls):
            env_key = f"TMP_{f.name.upper()}"
            if env_key in os.environ:
                raw = os.environ[env_key]
                data[f.name] = int(raw) if f.name in int_fields else raw

        return cls(**data)

    def ensure_vault_dir(self) -> Path:
        self.vault_dir.mkdir(parents=True, exist_ok=True)
        return self.vault_dir
