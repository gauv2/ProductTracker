import type { Listing } from "../types";
import { formatDate, formatDateTime, formatDistance, formatPrice } from "../lib/format";

const COLUMNS = ["Added", "Item", "Price", "Location", "Distance", "Posted", "Link"];

export function renderListingTable(container: HTMLElement, listings: Listing[], onOpen: (listing: Listing) => void): void {
	container.empty();
	const table = container.createEl("table", { cls: "tmp-listing-table" });

	const thead = table.createEl("thead");
	const headRow = thead.createEl("tr");
	for (const col of COLUMNS) {
		headRow.createEl("th", { text: col });
	}

	const tbody = table.createEl("tbody");
	for (const listing of listings) {
		const row = tbody.createEl("tr", { cls: listing.is_new ? "tmp-row-new" : "" });
		row.createEl("td", { text: formatDateTime(listing.seen_at) });
		const itemCell = row.createEl("td", { cls: "tmp-cell-item" });
		itemCell.createSpan({ text: listing.title });
		if (listing.is_new) itemCell.createSpan({ cls: "tmp-badge tmp-badge-new", text: "NEW" });
		row.createEl("td", { text: formatPrice(listing.price, listing.currency) });
		row.createEl("td", { text: listing.location || "—" });
		row.createEl("td", { text: formatDistance(listing.distance_km) });
		row.createEl("td", { text: formatDate(listing.posted_at) });
		const linkCell = row.createEl("td");
		const link = linkCell.createEl("a", { text: "Open ↗", href: listing.url });
		link.setAttribute("target", "_blank");
		link.setAttribute("rel", "noopener");
		link.onclick = (evt) => {
			evt.preventDefault();
			onOpen(listing);
		};
	}

	if (listings.length === 0) {
		const row = tbody.createEl("tr");
		const cell = row.createEl("td", { text: "No listings yet for this saved search." });
		cell.setAttribute("colspan", String(COLUMNS.length));
	}
}
