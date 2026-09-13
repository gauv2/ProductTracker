from trackmyproduct_daemon.vault.store import recompute_stats, stats_changed


def _listing(lid: str, price, seen_at="2026-01-01T00:00:00Z"):
    return {"id": lid, "price": price, "seen_at": seen_at}


def test_recompute_stats_empty_listings():
    stats = recompute_stats([])
    assert stats == {"all_time_high": None, "all_time_low": None}


def test_recompute_stats_picks_highest_and_lowest_priced_listing():
    listings = [
        _listing("l-1", 100),
        _listing("l-2", 500),
        _listing("l-3", 250),
    ]
    stats = recompute_stats(listings)
    assert stats["all_time_high"]["price"] == 500
    assert stats["all_time_high"]["listing_id"] == "l-2"
    assert stats["all_time_low"]["price"] == 100
    assert stats["all_time_low"]["listing_id"] == "l-1"


def test_recompute_stats_ignores_listings_without_numeric_price():
    listings = [
        _listing("l-1", None),
        _listing("l-2", 200),
    ]
    stats = recompute_stats(listings)
    assert stats["all_time_high"]["listing_id"] == "l-2"
    assert stats["all_time_low"]["listing_id"] == "l-2"


def test_stats_changed_detects_new_ath():
    old = recompute_stats([_listing("l-1", 100)])
    new = recompute_stats([_listing("l-1", 100), _listing("l-2", 200)])
    changed = stats_changed(old, new)
    assert changed["ath"] is True
    assert changed["atl"] is False


def test_stats_changed_detects_new_atl():
    old = recompute_stats([_listing("l-1", 100)])
    new = recompute_stats([_listing("l-1", 100), _listing("l-2", 50)])
    changed = stats_changed(old, new)
    assert changed["ath"] is False
    assert changed["atl"] is True


def test_stats_unchanged_when_same_records_hold():
    old = recompute_stats([_listing("l-1", 100), _listing("l-2", 200)])
    new = recompute_stats([_listing("l-1", 100), _listing("l-2", 200)])
    changed = stats_changed(old, new)
    assert changed == {"ath": False, "atl": False}


def test_stats_changed_from_no_prior_stats():
    old = {"all_time_high": None, "all_time_low": None}
    new = recompute_stats([_listing("l-1", 100)])
    changed = stats_changed(old, new)
    assert changed == {"ath": True, "atl": True}
