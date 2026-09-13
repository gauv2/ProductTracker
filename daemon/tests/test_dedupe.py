from trackmyproduct_daemon.vault.models import listing_id_for
from trackmyproduct_daemon.vault.store import dedupe_new_listings


def _candidate(platform: str, url: str, **extra) -> dict:
    return {"platform": platform, "url": url, "title": "t", "price": 100, **extra}


def test_listing_id_is_deterministic_for_same_platform_and_url():
    a = listing_id_for("marktplaats", "https://example.com/1")
    b = listing_id_for("marktplaats", "https://example.com/1")
    assert a == b


def test_listing_id_differs_for_different_url_or_platform():
    a = listing_id_for("marktplaats", "https://example.com/1")
    b = listing_id_for("marktplaats", "https://example.com/2")
    c = listing_id_for("ebay", "https://example.com/1")
    assert len({a, b, c}) == 3


def test_dedupe_skips_existing_platform_url_pairs():
    existing = [{"id": listing_id_for("marktplaats", "https://example.com/1")}]
    candidates = [
        _candidate("marktplaats", "https://example.com/1"),  # already seen -> dropped
        _candidate("marktplaats", "https://example.com/2"),  # new -> kept
    ]
    fresh = dedupe_new_listings(existing, candidates)
    assert len(fresh) == 1
    assert fresh[0]["url"] == "https://example.com/2"
    assert fresh[0]["id"] == listing_id_for("marktplaats", "https://example.com/2")


def test_dedupe_marks_new_listings_as_is_new():
    fresh = dedupe_new_listings([], [_candidate("ebay", "https://example.com/x")])
    assert fresh[0]["is_new"] is True


def test_dedupe_does_not_create_duplicates_within_same_candidate_batch():
    candidates = [
        _candidate("marktplaats", "https://example.com/1"),
        _candidate("marktplaats", "https://example.com/1"),
    ]
    fresh = dedupe_new_listings([], candidates)
    assert len(fresh) == 1


def test_dedupe_rescan_with_same_results_produces_no_new_listings():
    candidates = [_candidate("marktplaats", "https://example.com/1")]
    first_pass = dedupe_new_listings([], candidates)
    second_pass = dedupe_new_listings(first_pass, candidates)
    assert second_pass == []
