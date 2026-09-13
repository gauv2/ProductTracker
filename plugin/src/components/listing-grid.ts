import type { Listing } from "../types";
import { PLATFORM_LABEL, formatDate, formatDistance, formatPrice } from "../lib/format";

/**
 * data-model.md's listing schema has no image field, so the "image-forward"
 * tile (per the mockups) falls back to a platform-colored placeholder tile
 * instead of a real thumbnail. Noted in plugin/README.md as a judgment call.
 */
export function renderListingGrid(container: HTMLElement, listings: Listing[], onOpen: (listing: Listing) => void): void {
	container.empty();
	const grid = container.createDiv({ cls: "tmp-listing-grid" });

	for (const listing of listings) {
		const tile = grid.createDiv({ cls: "tmp-tile" });
		const thumb = tile.createDiv({ cls: `tmp-tile-thumb tmp-tile-thumb-${listing.platform}` });
		thumb.createSpan({ cls: "tmp-tile-platform", text: PLATFORM_LABEL[listing.platform] });
		if (listing.is_new) {
			thumb.createSpan({ cls: "tmp-badge tmp-badge-new tmp-tile-new-badge", text: "NEW" });
		}

		const body = tile.createDiv({ cls: "tmp-tile-body" });
		body.createDiv({ cls: "tmp-tile-title", text: listing.title });
		body.createDiv({ cls: "tmp-tile-price", text: formatPrice(listing.price, listing.currency) });
		body.createDiv({
			cls: "tmp-tile-meta",
			text: `${listing.location || "—"} · ${formatDistance(listing.distance_km)} · ${formatDate(listing.posted_at)}`,
		});

		tile.onClickEvent(() => onOpen(listing));
	}

	if (listings.length === 0) {
		grid.createDiv({ cls: "tmp-empty-state", text: "No listings yet for this saved search." });
	}
}
