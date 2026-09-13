# TrackMyProduct Daemon

Local Python service for TrackMyProduct: owns the Obsidian vault notes
(read/write), exposes the local HTTP API the GUI talks to, and runs the
scheduled marketplace scans + notifications. See `../docs/data-model.md`
and `../docs/api-contract.md` (repo root `docs/`) for the frozen contracts
this implements.

No cloud dependency — everything (vault, API, scheduler) runs on your own
machine. The only outbound network calls are to the marketplaces you've
configured, Telegram, and (optionally) Google/Tweakers for new-price
lookups.

## Package layout

```
daemon/
  src/trackmyproduct_daemon/
    config.py            # Config dataclass, loaded from JSON + env vars
    main.py              # entrypoint: starts API + scheduler together
    scan.py              # scan-cycle orchestration (pure logic + IO glue)
    price_history.py     # derives chart points from listings[] at read time
    vault/
      frontmatter.py     # Markdown + YAML frontmatter read/write
      store.py           # CRUD over product notes, dedupe/ATH-ATL logic
      models.py           # id generation, empty-product/saved-search shapes
    adapters/
      base.py             # Listing / SearchFilters / PlatformAdapter interface
      marktplaats.py       # real, reference implementation
      ebay.py               # real, against the official Browse API
      facebook.py           # best-effort, isolated (see caveats below)
    notifications/
      telegram.py          # real
      base.py               # pluggable interface (Rakazo/Grok Bot: future)
    pricing/
      google.py             # new-price lookup via Custom Search JSON API
      tweakers.py            # new-price lookup, best-effort (see caveats)
    api/
      app.py                 # FastAPI routes per docs/api-contract.md
      schemas.py              # request/response models
      errors.py                # standard {error:{code,message}} shape
  tests/                        # pytest: frontmatter round-trip, dedupe, ATH/ATL
  pyproject.toml
```

## Setup

Requires Python 3.11+.

```bash
cd daemon
python -m venv .venv
source .venv/Scripts/activate   # Windows Git Bash; use .venv\Scripts\activate.bat for cmd.exe
pip install -e ".[dev]"
```

### Configuration

The daemon reads a JSON config file, default `~/.trackmyproduct/config.json`
(override the path with `TMP_CONFIG_PATH`). Any field can also be set via
an environment variable `TMP_<FIELD_NAME_UPPERCASE>` (e.g. `TMP_VAULT_PATH`,
`TMP_TELEGRAM_BOT_TOKEN`) — env vars win over the file, useful for secrets
you don't want written to disk.

Example `~/.trackmyproduct/config.json`:

```json
{
  "vault_path": "C:/Users/you/Obsidian/YourVault/TrackMyProduct",
  "scan_interval_minutes": 15,
  "telegram_bot_token": "123456:ABC-your-bot-token",
  "telegram_chat_id": "123456789",
  "ebay_client_id": "your-ebay-app-client-id",
  "ebay_client_secret": "your-ebay-app-client-secret",
  "ebay_marketplace_id": "EBAY_NL",
  "facebook_cookie": "",
  "tweakers_cookie": "",
  "google_api_key": "",
  "google_cse_id": ""
}
```

All fields have defaults except `vault_path`, which you should point at
your actual Obsidian vault's `TrackMyProduct/` folder (or wherever you want
product notes to live — it's created automatically if missing).

### Telegram bot token (required for notifications)

1. Open a chat with `@BotFather` on Telegram, send `/newbot`, follow the
   prompts. It gives you a token like `123456:ABC-...` — put it in
   `telegram_bot_token`.
2. Send any message to your new bot from the Telegram account you want
   notifications on.
3. Visit `https://api.telegram.org/bot<your-token>/getUpdates` in a browser
   and find `"chat":{"id": ...}` in the JSON — that numeric id is
   `telegram_chat_id`.

Without both fields set, the daemon logs a warning and skips sending (it
does not crash the scan cycle).

### eBay app token setup (required for the eBay adapter)

The eBay adapter uses the official **Browse API** with a client-credentials
application token — never scraping, per the contract.

1. Register at https://developer.ebay.com/ and create an application (the
   free tier's rate limits are generous enough for periodic scans).
2. From your app's keys page, copy the **Client ID** and **Client Secret**
   into `ebay_client_id` / `ebay_client_secret`.
3. Set `ebay_marketplace_id` to the marketplace you want to search (e.g.
   `EBAY_NL`, `EBAY_DE`, `EBAY_GB`, `EBAY_US`).

The daemon requests and caches an application access token itself (client
credentials grant) — no manual token refresh needed. Without credentials
configured, the eBay adapter raises a contained `AdapterError` per search,
which the scan cycle logs and skips (it never blocks Marktplaats).

### Vault path

Point `vault_path` at the folder inside your Obsidian vault where product
notes should live. The daemon creates the folder if it doesn't exist and
only ever touches `.md` files with `tmp_type: product` in their
frontmatter — it never touches anything else in your vault.

## Running

```bash
# from daemon/, with the venv activated
python -m trackmyproduct_daemon.main
# or, after `pip install -e .`:
trackmyproduct-daemon
```

This starts the FastAPI server (default `http://127.0.0.1:8756`, per
`docs/api-contract.md`) and the background scheduler in one process. The
scheduler runs all enabled saved searches every `scan_interval_minutes`
(default 15); the first cycle fires after one interval, not immediately on
startup. Trigger an immediate out-of-band scan for one saved search via
`POST /products/{id}/saved-searches/{sid}/scan`.

## Tests

```bash
cd daemon
source .venv/Scripts/activate
python -m pytest -q
```

26 tests cover: the frontmatter read/write round-trip (including a missing
frontmatter block and body preservation), listing dedupe by
`(platform, url)` including re-scan idempotency, all-time-high/low
recomputation and change detection, product CRUD over the vault, and
notification queuing/dedupe.

## Platform adapters — what's real, what's best-effort

### Marktplaats (real, reference implementation)

Uses Marktplaats' own unofficial search JSON endpoint
(`GET https://www.marktplaats.nl/lrp/api/search`) — the same one their web
frontend calls. There is no official public search API. This was verified
manually against the live endpoint on 2026-09-13 (see
`adapters/marktplaats.py`'s module docstring for the exact response shape
observed). It's undocumented and can change without notice; the adapter
degrades to an `AdapterError` (caught per-search by the scan cycle) rather
than crashing if the shape changes enough to break parsing outright, but a
smaller schema drift could silently return partial/wrong data — worth
spot-checking after long gaps between runs.

### eBay (real, official Browse API)

Implemented against `https://api.ebay.com/buy/browse/v1/item_summary/search`
with a cached client-credentials token. Requires the app credentials setup
above. No scraping.

### Facebook Marketplace (best-effort, isolated — read this)

**There is no reliable way to query Facebook Marketplace with plain HTTP
requests.** Confirmed by manual testing (2026-09-13): its search results
are rendered client-side by JavaScript, and anonymous requests to the
lightweight `mbasic.facebook.com` HTML version are redirected to a login
wall. This adapter:

- Does nothing (returns `[]`, logs a warning) unless you configure
  `facebook_cookie` with a `Cookie` header copied from a browser session
  that's actually logged into Facebook. This cookie **will expire**
  periodically and needs manual refreshing — there's no automated login
  flow here (and building one would violate Facebook's ToS).
- Scrapes `mbasic.facebook.com`'s server-rendered HTML with best-effort
  regex/BeautifulSoup parsing. Facebook's markup changes without notice and
  this **will** break silently from time to time — that's expected.
- **Never raises out of its `search()` method.** Any exception (network,
  parsing, unexpected markup) is caught internally and logged; the scan
  cycle additionally wraps every adapter call, so a Facebook failure can
  never block Marktplaats or eBay scans for the same saved search.

If you need reliable Facebook Marketplace coverage, the realistic options
are a headless browser with a persistent logged-in profile, or a paid
third-party scraping API — neither is implemented here; a fragile scraper
that's honest about its fragility is more useful than a "working" one that
silently returns nothing.

## New-price lookup (Google + Tweakers)

`POST /products/{id}/refresh-new-price` tries Tweakers Pricewatch first,
then falls back to Google. Both are best-effort:

- **Tweakers**: confirmed by manual testing (2026-09-13) that anonymous
  requests to `tweakers.net/pricewatch/zoeken/` are redirected to a DPG
  Media cookie-consent wall before reaching any content — there's no way
  past this with a plain HTTP request. Set `tweakers_cookie` (captured from
  a browser session that's already clicked through the consent flow) to
  make this work at all; without it, the lookup always returns `None`,
  which is the documented, expected behavior.
- **Google**: rather than scraping `google.com/search` (against Google's
  ToS and aggressively blocked), this uses the official **Custom Search
  JSON API** (Programmable Search Engine). Requires `google_api_key` and
  `google_cse_id` — see setup links in `pricing/google.py`'s module
  docstring. Free tier is 100 queries/day. Price extraction is a regex over
  result titles/snippets — treat results as "roughly what this costs new,"
  not authoritative pricing.

## Discrepancies / judgment calls vs. the docs

Per the ownership rules, `docs/*.md` were not edited — noting the following
here instead:

- **`sort=best` formula.** `docs/api-contract.md` and
  `docs/product-brief.md` mention a "combined price + distance score" for
  the `best` sort but don't define the formula. Implemented as
  `price + distance_km * 10` (a simple linear penalty) in
  `api/app.py::_best_score` — reasonable, not authoritative; adjust the
  constant if it doesn't feel right in practice.
- **Price-history bucketing threshold.** `docs/data-model.md` says the
  chart groups "by day (or week for long ranges)" without a cutoff.
  `price_history.py` buckets by day for `period` ∈ {1m, 3m, 6m} and by ISO
  week for {year, all}.
- **Saved-search / product request bodies.** `docs/api-contract.md` lists
  routes and purposes but not exact JSON request shapes for
  `POST /products`, saved-search create/patch, etc. `api/schemas.py`
  mirrors the field names and types from `docs/data-model.md`'s frontmatter
  schema directly.
- **Marktplaats server-side filters unverified.** Passing `postcode` /
  `distanceMeters` / `priceFrom` / `priceTo` query params to the Marktplaats
  search endpoint did not visibly change results during manual testing, so
  the adapter treats server-side filtering as unreliable and always
  re-applies `title_includes` / `exclude_words` / price / distance filters
  client-side (`adapters/base.py::apply_client_side_filters`) as the source
  of truth, per every adapter.
