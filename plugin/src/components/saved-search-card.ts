import type { Product, SavedSearch } from "../types";
import { PLATFORM_LABEL, formatRelative } from "../lib/format";

export interface SavedSearchCardCallbacks {
	onOpen: (product: Product, search: SavedSearch) => void;
	onRefresh: (product: Product, search: SavedSearch) => void;
	onEdit: (product: Product, search: SavedSearch) => void;
	onDelete: (product: Product, search: SavedSearch) => void;
	onToggle: (product: Product, search: SavedSearch) => void;
}

export function renderSavedSearchCard(
	container: HTMLElement,
	product: Product,
	search: SavedSearch,
	callbacks: SavedSearchCardCallbacks
): void {
	const card = container.createDiv({ cls: "tmp-card" });

	const header = card.createDiv({ cls: "tmp-card-header" });
	const titleWrap = header.createDiv({ cls: "tmp-card-title-wrap" });
	titleWrap.createEl("div", { cls: "tmp-card-product", text: product.name });
	titleWrap.createEl("div", { cls: "tmp-card-label", text: search.label || search.query });

	const badges = header.createDiv({ cls: "tmp-badges" });
	for (const platform of search.platforms) {
		badges.createSpan({ cls: `tmp-badge tmp-badge-${platform}`, text: PLATFORM_LABEL[platform] });
	}
	if (!search.enabled) {
		badges.createSpan({ cls: "tmp-badge tmp-badge-disabled", text: "Paused" });
	}

	const listings = product.listings.filter((l) => l.saved_search_id === search.id);
	const newCount = listings.filter((l) => l.is_new).length;

	const stats = card.createDiv({ cls: "tmp-card-stats" });
	const countEl = stats.createDiv({ cls: "tmp-card-count" });
	countEl.createSpan({ text: `${listings.length} result${listings.length === 1 ? "" : "s"}` });
	if (newCount > 0) {
		countEl.createSpan({ cls: "tmp-badge tmp-badge-new", text: `+${newCount} new` });
	}
	stats.createDiv({ cls: "tmp-card-scanned", text: `Last scanned ${formatRelative(search.last_scanned_at)}` });

	card.onClickEvent((evt) => {
		if ((evt.target as HTMLElement).closest(".tmp-card-actions")) return;
		callbacks.onOpen(product, search);
	});

	const actions = card.createDiv({ cls: "tmp-card-actions" });

	const refreshBtn = actions.createEl("button", { cls: "tmp-icon-btn", attr: { "aria-label": "Refresh" } });
	refreshBtn.setText("↻");
	refreshBtn.onclick = () => callbacks.onRefresh(product, search);

	const toggleBtn = actions.createEl("button", { cls: "tmp-icon-btn", attr: { "aria-label": "Toggle enabled" } });
	toggleBtn.setText(search.enabled ? "⏸" : "▶");
	toggleBtn.onclick = () => callbacks.onToggle(product, search);

	const editBtn = actions.createEl("button", { cls: "tmp-icon-btn", attr: { "aria-label": "Edit" } });
	editBtn.setText("✎");
	editBtn.onclick = () => callbacks.onEdit(product, search);

	const deleteBtn = actions.createEl("button", { cls: "tmp-icon-btn tmp-icon-btn-danger", attr: { "aria-label": "Delete" } });
	deleteBtn.setText("🗑");
	deleteBtn.onclick = () => callbacks.onDelete(product, search);
}
