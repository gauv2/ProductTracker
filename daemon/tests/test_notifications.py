from trackmyproduct_daemon.scan import build_queued_notifications


def _product(name="Product", notifications_sent=None):
    return {"name": name, "notifications_sent": notifications_sent or []}


def test_ath_notification_queued_once():
    old_stats = {"all_time_high": {"price": 100, "listing_id": "l-1"}, "all_time_low": None}
    new_stats = {"all_time_high": {"price": 200, "listing_id": "l-2"}, "all_time_low": None}
    product = _product()
    notifications = build_queued_notifications(product, [], [], old_stats, new_stats)
    assert any(n.key == "ath:l-2" for n in notifications)


def test_ath_notification_deduped_if_already_sent():
    old_stats = {"all_time_high": {"price": 100, "listing_id": "l-1"}, "all_time_low": None}
    new_stats = {"all_time_high": {"price": 200, "listing_id": "l-2"}, "all_time_low": None}
    product = _product(notifications_sent=[{"key": "ath:l-2", "sent_at": "2026-01-01T00:00:00Z"}])
    notifications = build_queued_notifications(product, [], [], old_stats, new_stats)
    assert not any(n.key == "ath:l-2" for n in notifications)


def test_cross_platform_match_notification_for_new_platform():
    old_listings = [{"platform": "marktplaats", "id": "l-1"}]
    new_listings = [{"platform": "ebay", "id": "l-2", "seen_at": "2026-01-01T00:00:00Z"}]
    stats = {"all_time_high": None, "all_time_low": None}
    product = _product()
    notifications = build_queued_notifications(product, old_listings, new_listings, stats, stats)
    assert any(n.key == "cross-platform:ebay:2026-01-01" for n in notifications)


def test_no_cross_platform_notification_for_already_seen_platform():
    old_listings = [{"platform": "marktplaats", "id": "l-1"}]
    new_listings = [{"platform": "marktplaats", "id": "l-2", "seen_at": "2026-01-01T00:00:00Z"}]
    stats = {"all_time_high": None, "all_time_low": None}
    product = _product()
    notifications = build_queued_notifications(product, old_listings, new_listings, stats, stats)
    assert notifications == []
