# TrackMyProduct (Obsidian plugin)

GUI half of the TrackMyProduct system described in `../docs/product-brief.md`.
Reads tracked-product notes straight from the vault (via Obsidian's
Vault/MetadataCache API — no direct file I/O) so browsing works even with the
daemon turned off, and talks to the local daemon API
(`http://127.0.0.1:8756` by default, see `../docs/api-contract.md`) only for
things that actually need it: creating/editing saved searches, triggering a
scan, marking a listing seen, deleting a listing.

## Build

```sh
cd plugin
npm install
npm run build   # tsc typecheck + esbuild bundle -> main.js
```

`npm run dev` runs esbuild in watch mode for iterating against a live vault.

## Load it into a test vault

A ready-made scratch vault with sample data lives at `plugin/sample-vault/`.

1. Build the plugin (`npm install && npm run build` — see above).
2. Open `plugin/sample-vault/` as a vault in Obsidian (or copy/symlink the
   whole `plugin/` folder's build output into an existing vault, see below).
3. Symlink or copy the plugin into that vault's plugins folder:

   ```sh
   # from plugin/sample-vault/.obsidian/plugins/
   mkdir -p trackmyproduct
   cp ../../../manifest.json ../../../main.js ../../../styles.css trackmyproduct/
   ```

   or, to keep iterating without re-copying on every build, symlink instead
   of copying (PowerShell, run as/with permission to create symlinks):

   ```powershell
   New-Item -ItemType SymbolicLink -Path "sample-vault\.obsidian\plugins\trackmyproduct" -Target "..\..\.."
   ```

   (adjust the relative target so it points at `plugin/` itself, which
   contains `manifest.json` + `main.js` + `styles.css` after a build).
4. The sample vault's `.obsidian/community-plugins.json` already lists
   `trackmyproduct`, so Obsidian enables it automatically on open — if you
   used a different vault, enable it manually under Settings → Community
   plugins.
5. Click the shopping-cart ribbon icon (or run the "Open marketplace view"
   command) to open the Marketplace view.

`sample-vault/TrackMyProduct/` contains two product notes with frontmatter
matching `../docs/data-model.md` exactly, so both views render populated
data immediately, before any daemon is running:

- `nvidia-dgx-spark.md` — one saved search targeting Marktplaats + eBay, 11
  listings spread over ~6 months (enough for the price chart to draw two
  series and an annotation line), two of them flagged `is_new: true`.
- `herman-miller-aeron.md` — two saved searches on the same product: one
  enabled (eBay, with listings) and one **paused** with no listings yet, to
  show the "Paused" badge and the empty-listings state.

Point the daemon (once you have one) at the same vault and the plugin will
pick up its writes automatically — the views re-render on
`metadataCache.on("changed")`.

## Views

- **Marketplace** (`trackmyproduct-marketplace`, ribbon icon + command "Open
  marketplace view") — a Marktplaats/eBay/Both tab strip, a "+ Add" form
  (product name with autocomplete over existing products, label, platforms,
  query, title-must-include, exclude words, min/max price, distance,
  postcode), and a card per saved search (across all products) showing its
  platform badge(s), result count with a "+N new" delta, last-scanned time,
  and refresh / toggle-enabled / edit / delete actions. Clicking a card
  (outside its action buttons) opens that saved search's Listings view.
- **Listings** (`trackmyproduct-listings`, opened from a Marketplace card) —
  header with product name + saved-search label + count, a price-history
  chart, sort pills (Newest / Cheapest / Nearest / Best), and a grid/list
  toggle. Grid is image-forward tile cards with a platform-colored thumbnail,
  a "NEW" badge and price; list is a table with columns Added, Item, Price,
  Location, Distance, Posted, Link — "Link" opens the source ad in the
  default browser (`window.open`). Opening this view marks that saved
  search's `is_new` listings as seen via the daemon (data-model.md: "`is_new`
  is cleared by the GUI... not by the daemon") and shows an inline notice if
  the daemon isn't reachable, instead of silently failing.
- **Price history chart** — hand-rolled inline SVG (no bundled charting
  library): two series (Minimum solid, Gemiddelde/Average dashed), a euro
  y-axis, month ticks on the x-axis, period buttons (1m/3m/6m/Jaar/Alles),
  and a dashed red annotation line for the lowest price in the last 6
  months. Computed client-side from `listings[]` per data-model.md ("Price
  history for the chart... is derived, not stored... compute it... at read
  time"), so it renders correctly with the daemon offline.
- **Settings tab** — products folder (default `TrackMyProduct/`) and daemon
  API base URL (default `http://127.0.0.1:8756`).

## Judgment calls (contract left these open; docs/*.md were not edited)

- **Platform tabs' scope.** The brief lists "platform tabs (Marktplaats /
  eBay / Both)" next to the search-config row without saying whether they
  filter the existing card list or just seed the "+ Add" form's platform
  selection. Implemented as the latter (a preset for the form) since a
  saved search's own platform badges already convey its target(s) on its
  card, and a filter would hide cards without an obvious way to reveal them
  again in a single-tab UI.
- **One product field instead of a product picker.** Saved searches nest
  under a product note in the data model, but the Marketplace screen in the
  brief has no visible product selector. The "+ Add" form uses one text
  input with an autocomplete `<datalist>` of existing product names: an
  exact match attaches the new search to that product, anything else calls
  `POST /products` first. Keeps "+ Add" a single step.
- **No image field in the data model.** `listings[]` has no thumbnail URL,
  so the "image-forward" grid tiles use a platform-colored placeholder
  (with the platform name) instead of a real photo. Nothing was added to
  the frontmatter schema to avoid touching the frozen contract.
- **"Best" sort.** Not defined beyond "combined price + distance score".
  Implemented as a per-result-set min-max normalization of price and
  distance, blended 65/35 in favor of price, falling back to price-only
  when a listing (or the whole set, e.g. eBay-only) has no `distance_km`.
  See `src/lib/listings.ts`.
- **Chart period vs. daemon's `/price-history` endpoint.** The API contract
  exposes `GET /products/{id}/price-history`, but data-model.md is explicit
  that history is derived from `listings[]` "at read time, in whichever
  side renders the chart" — so the GUI computes it locally instead of
  calling the daemon, which is also what keeps the chart usable read-only.
  The range-brush scrubber shown in the brief's mockups was left out; only
  the explicitly-required preset period buttons are implemented.
- **Marking listings seen.** The API contract's `PATCH .../listings/{lid}`
  is per-listing with no bulk variant, so opening a Listings view loops over
  that search's `is_new` listings and calls it for each; if the first call
  fails (daemon unreachable) the rest are skipped and a single inline notice
  is shown rather than one per listing.

## Constraints followed

- TypeScript, Obsidian's official `obsidian` npm package for types, esbuild
  bundle to a single `main.js` — the standard community-plugin scaffold.
- No Node/Electron file I/O: all vault reads go through
  `app.vault.getMarkdownFiles()` / `app.metadataCache.getFileCache()`
  (`src/lib/vault-data.ts`); all daemon writes go through `fetch` in
  `src/lib/api-client.ts`, never direct file writes.
- Every daemon call returns `{ ok: true, data } | { ok: false, error }`
  instead of throwing, so an offline daemon shows an inline `Notice` /
  status line rather than crashing a view.
