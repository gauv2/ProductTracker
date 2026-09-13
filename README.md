# TrackMyProduct

A local-first system for tracking second-hand product listings across
marketplaces, storing price history, and surfacing trends and deals — an
Obsidian vault as the database, an Obsidian plugin as the GUI, and a Python
daemon that does the scanning.

See `docs/product-brief.md` for the full spec, `docs/data-model.md` for the
vault note schema, and `docs/api-contract.md` for the daemon's local HTTP API.

## Components

- **`/daemon`** — Python service. Scans saved searches across Marktplaats
  (real), eBay (real, official Browse API) and Facebook Marketplace
  (best-effort, isolated), tracks all-time high/low, sends Telegram
  notifications, and exposes a local CRUD API. See `daemon/README.md`.
- **`/plugin`** — Obsidian plugin (TypeScript). Marketplace and listings
  views, grid/list toggle, a price-history chart, all readable straight from
  the vault with no daemon required, plus daemon-backed actions (add/edit a
  saved search, trigger a scan). See `plugin/README.md`.

## Quick start (running both together)

```bash
# 1. Daemon
cd daemon
python -m venv .venv && source .venv/Scripts/activate   # .venv\Scripts\activate on cmd.exe
pip install -e ".[dev]"
# point it at a real vault folder, e.g.:
export TMP_VAULT_PATH="/path/to/YourVault/TrackMyProduct"
python -m trackmyproduct_daemon.main   # serves http://127.0.0.1:8756

# 2. Plugin (separate terminal)
cd plugin
npm install && npm run build
# copy/symlink manifest.json, main.js, styles.css into
# <YourVault>/.obsidian/plugins/trackmyproduct/, then enable it in Obsidian
```

Both default to the same local API base URL (`http://127.0.0.1:8756`), and
the plugin's Settings tab lets you point it at a different vault subfolder or
daemon URL. The plugin works read-only against the vault even with the
daemon stopped; only saved-search create/edit, triggering a scan, and
marking listings seen need the daemon running.

Verified end-to-end: daemon's 26 pytest tests pass, a live daemon correctly
serves the full product → saved-search → listings → price-history flow and
writes valid frontmatter notes, and `npm run build` produces a working
`main.js` with no type errors.

## Known gaps (see component READMEs for detail)

- Facebook Marketplace and Tweakers Pricewatch need a manually-captured
  session cookie (no public API for either); eBay and Google price lookups
  need your own free-tier API credentials.
- The plugin's price chart doesn't yet implement the range-brush scrubber
  from the original mockups — only the preset period buttons (1m/3m/6m/Jaar/Alles).
