"""Entrypoint: starts the scheduler alongside the API server in one process.

Run with ``python -m trackmyproduct_daemon.main`` or the
``trackmyproduct-daemon`` console script installed by pyproject.toml.
"""

from __future__ import annotations

import logging

import uvicorn
from apscheduler.schedulers.background import BackgroundScheduler

from .adapters import ADAPTER_REGISTRY
from .api import create_app
from .config import Config
from .notifications import TelegramChannel
from .scan import run_scan_cycle
from .vault.models import utc_now_iso
from .vault.store import VaultStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def run() -> None:
    config = Config.load()
    app = create_app(config)
    store: VaultStore = app.state.store

    def scheduled_scan() -> None:
        logger.info("running scheduled scan cycle")
        adapters = {
            "marktplaats": ADAPTER_REGISTRY["marktplaats"](base_url=config.marktplaats_base_url),
            "ebay": ADAPTER_REGISTRY["ebay"](
                client_id=config.ebay_client_id,
                client_secret=config.ebay_client_secret,
                marketplace_id=config.ebay_marketplace_id,
            ),
            "facebook": ADAPTER_REGISTRY["facebook"](
                cookie=config.facebook_cookie, locale=config.facebook_locale
            ),
        }
        channels = [TelegramChannel(config.telegram_bot_token, config.telegram_chat_id)]
        try:
            run_scan_cycle(store, adapters, channels)
        except Exception:  # noqa: BLE001 - never let the scheduler thread die
            logger.exception("scan cycle failed")
        finally:
            app.state.last_scan_cycle_at = utc_now_iso()

    scheduler = BackgroundScheduler()
    scheduler.add_job(
        scheduled_scan,
        "interval",
        minutes=config.scan_interval_minutes,
        id="scan_cycle",
    )
    scheduler.start()
    logger.info(
        "scheduler started: scanning every %s minutes, vault at %s",
        config.scan_interval_minutes,
        config.vault_dir,
    )

    try:
        uvicorn.run(app, host=config.host, port=config.port)
    finally:
        scheduler.shutdown(wait=False)


if __name__ == "__main__":
    run()
