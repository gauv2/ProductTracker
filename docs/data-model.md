# TrackMyProduct — vault data model

One Markdown note per tracked product, living under a configurable vault folder
(default: `TrackMyProduct/`). Frontmatter carries every structured field; the
note body is free for the user's own notes and is never touched by the daemon.

## Frontmatter schema

```yaml
---
tmp_id: "a1b2c3"              # stable id, generated once, never reused
tmp_type: product
name: "NVIDIA DGX Spark"
category: "Computer hardware"
created_at: "2026-09-13T12:00:00Z"
updated_at: "2026-09-13T12:00:00Z"

saved_searches:
  - id: "ss-1"
    label: "Nvidia DGX"
    platforms: [marktplaats, ebay]   # subset of: marktplaats, ebay, facebook
    query: "Nvidia DGX"
    title_includes: ["yamaha"]        # comma-separated in UI, array on disk; all must match
    exclude_words: []
    min_price: null
    max_price: null
    mp_distance_km: null              # marktplaats only
    mp_postcode: null                 # marktplaats only
    enabled: true
    last_scanned_at: "2026-09-13T12:10:00Z"

listings:
  - id: "l-9f3a"
    saved_search_id: "ss-1"
    platform: marktplaats
    title: "Lenovo ThinkStation PGX Nvidia..."
    price: 4999
    currency: EUR
    location: "Rotterdam"
    distance_km: 0.0
    posted_at: "2026-08-17T00:00:00Z"
    seen_at: "2026-09-12T08:28:00Z"
    url: "https://..."
    is_new: true                      # true until the GUI/user views it

stats:
  all_time_high: { price: 6129.84, listing_id: "l-...", at: "2026-09-13T00:03:00Z" }
  all_time_low:  { price: 819.04,  listing_id: "l-...", at: "2026-09-09T17:50:47Z" }

new_price:
  price: null
  currency: EUR
  source: null          # "google" | "tweakers"
  source_url: null
  fetched_at: null

notifications_sent:
  - key: "ath:l-...."          # dedupe key, one of: ath:<listing_id>, atl:<listing_id>, cross-platform:<platform>:<date>
    sent_at: "2026-09-13T00:03:30Z"
---
```

## Invariants

- `tmp_id` is assigned once by whichever side creates the note (GUI or daemon) and is
  never regenerated.
- `listings[].id` is derived deterministically from `(platform, url)` so re-scans
  don't create duplicates — recompute and skip-if-exists rather than trusting scrape order.
- `is_new` is cleared by the GUI when the user opens/views that saved search's
  listings, not by the daemon.
- `stats.*` and `new_price` are daemon-owned derived fields; the GUI treats them
  as read-only display data.
- `notifications_sent` is append-only and is how the daemon avoids re-notifying
  on the same event after a restart.

## Price history for the chart

The chart (Minimum / Gemiddelde per period) is *derived*, not stored — compute
it from `listings[]` grouped by day (or week for long ranges) at read time, in
whichever side renders the chart. Do not maintain a separate parallel history
array; `listings[]` is the single source of truth.
