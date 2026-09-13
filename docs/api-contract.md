# TrackMyProduct — daemon local API contract (v1)

Local-only HTTP API, default `http://127.0.0.1:8756`. No auth (localhost-bound
only). JSON in/out. All shapes below mirror `docs/data-model.md` frontmatter —
the daemon is the only writer of derived fields (`stats`, `new_price`,
`notifications_sent`); the GUI is the only writer of `is_new`.

| Method | Path                                   | Purpose                                              |
| ------ | --------------------------------------- | ----------------------------------------------------- |
| GET    | `/products`                             | List all products (summary: id, name, stats, counts)  |
| POST   | `/products`                             | Create a product note                                 |
| GET    | `/products/{id}`                        | Full product incl. listings + saved searches          |
| PATCH  | `/products/{id}`                        | Edit product fields (name, category)                  |
| DELETE | `/products/{id}`                        | Delete the product note                                |
| POST   | `/products/{id}/saved-searches`         | Add a saved search                                     |
| PATCH  | `/products/{id}/saved-searches/{sid}`   | Edit a saved search (incl. `enabled` toggle)           |
| DELETE | `/products/{id}/saved-searches/{sid}`   | Remove a saved search                                  |
| POST   | `/products/{id}/saved-searches/{sid}/scan` | Trigger an immediate out-of-band scan                |
| GET    | `/products/{id}/listings`               | Listings, query params: `sort=newest\|cheapest\|nearest\|best`, `saved_search_id` |
| PATCH  | `/products/{id}/listings/{lid}`         | GUI marks `is_new: false`                              |
| DELETE | `/products/{id}/listings/{lid}`         | Remove a bad/irrelevant listing                        |
| GET    | `/products/{id}/price-history`          | Query params: `period=1m\|3m\|6m\|year\|all` → `{ points: [{date, min, avg}] }` |
| POST   | `/products/{id}/refresh-new-price`      | Re-run Google/Tweakers lookup for current new price    |
| GET    | `/health`                               | `{ status: "ok", daemon_version, last_scan_cycle_at }` |

## Scan cycle

The daemon runs all `enabled: true` saved searches on a fixed interval
(default 15 min, configurable via daemon config file). Each cycle, per saved
search:

1. Fetch listings from each targeted platform.
2. Filter by `title_includes` / `exclude_words` / price / distance.
3. Diff against existing `listings[]` by `(platform, url)`; append new ones with `is_new: true`.
4. Recompute `stats.all_time_high` / `all_time_low`; if either changed, queue an ATH/ATL notification.
5. If a listing's platform wasn't previously present in `listings[]` for this product, queue a cross-platform-match notification.
6. Send queued notifications (Telegram first; other channels are additive), recording each in `notifications_sent` for dedupe.

## Platform adapters

Each platform is an interchangeable adapter behind one interface —
`search(query, filters) -> Listing[]`:

- **Marktplaats** — primary/reference implementation, first to build.
- **eBay** — use the official Browse API (requires an application/user token);
  do not scrape eBay.
- **Facebook Marketplace** — no public API; treat as best-effort and isolate
  failures so one broken adapter never blocks the others' scan cycle.

## Errors

Standard shape: `{ "error": { "code": "not_found" | "validation_error" | "upstream_unavailable", "message": "..." } }`
with matching HTTP status (404, 422, 502).
