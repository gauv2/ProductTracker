import { ItemView, Notice, ViewStateResult, WorkspaceLeaf } from "obsidian";
import type TrackMyProductPlugin from "../main";
import type { Listing, Period, SortMode, ViewMode } from "../types";
import { sortListings } from "../lib/listings";
import { computePriceHistory, lowestInMonths } from "../lib/price-history";
import { renderPriceChart } from "../components/price-chart";
import { renderListingGrid } from "../components/listing-grid";
import { renderListingTable } from "../components/listing-table";

export const VIEW_TYPE_LISTINGS = "trackmyproduct-listings";

interface ListingsViewState {
	productId: string;
	savedSearchId: string;
}

const SORT_OPTIONS: { key: SortMode; label: string }[] = [
	{ key: "newest", label: "Newest" },
	{ key: "cheapest", label: "Cheapest" },
	{ key: "nearest", label: "Nearest" },
	{ key: "best", label: "Best" },
];

const ANNOTATION_MONTHS = 6;

export class ListingsView extends ItemView {
	private plugin: TrackMyProductPlugin;
	private state: ListingsViewState | null = null;
	private sortMode: SortMode = "newest";
	private viewMode: ViewMode = "grid";
	private period: Period = "6m";
	private markedSeenFor: string | null = null;

	constructor(leaf: WorkspaceLeaf, plugin: TrackMyProductPlugin) {
		super(leaf);
		this.plugin = plugin;
	}

	getViewType(): string {
		return VIEW_TYPE_LISTINGS;
	}

	getDisplayText(): string {
		if (!this.state) return "Listings";
		const product = this.plugin.vaultData.getProductById(this.state.productId);
		const search = product?.saved_searches.find((s) => s.id === this.state?.savedSearchId);
		return search ? `${product?.name} · ${search.label}` : "Listings";
	}

	getIcon(): string {
		return "list";
	}

	async setState(state: ListingsViewState, result: ViewStateResult): Promise<void> {
		this.state = state;
		this.render();
		await super.setState(state, result);
	}

	getState(): Record<string, unknown> {
		return { ...(this.state ?? {}) };
	}

	async onOpen(): Promise<void> {
		this.render();
		this.registerEvent(this.app.metadataCache.on("changed", () => this.render()));
	}

	private render(): void {
		const container = this.containerEl.children[1] as HTMLElement;
		container.empty();
		container.addClass("tmp-view");

		if (!this.state) {
			container.createDiv({ cls: "tmp-empty-state", text: "Open this view from a saved search's card." });
			return;
		}

		const product = this.plugin.vaultData.getProductById(this.state.productId);
		if (!product) {
			container.createDiv({
				cls: "tmp-empty-state",
				text: "Could not find this product in the vault anymore.",
			});
			return;
		}
		const search = product.saved_searches.find((s) => s.id === this.state?.savedSearchId);
		if (!search) {
			container.createDiv({
				cls: "tmp-empty-state",
				text: "Could not find this saved search on the product anymore.",
			});
			return;
		}

		const listings = product.listings.filter((l) => l.saved_search_id === search.id);

		const header = container.createDiv({ cls: "tmp-header" });
		const titleWrap = header.createDiv();
		titleWrap.createEl("h2", { text: product.name });
		titleWrap.createEl("div", { cls: "tmp-subtitle", text: `${search.label} · ${listings.length} listings` });

		const chartSection = container.createDiv({ cls: "tmp-section" });
		this.renderChart(chartSection, listings);

		const toolbar = container.createDiv({ cls: "tmp-toolbar" });
		const sortRow = toolbar.createDiv({ cls: "tmp-tabs" });
		for (const opt of SORT_OPTIONS) {
			const btn = sortRow.createEl("button", {
				cls: `tmp-pill ${opt.key === this.sortMode ? "tmp-pill-active" : ""}`,
				text: opt.label,
			});
			btn.onclick = () => {
				this.sortMode = opt.key;
				this.render();
			};
		}

		const viewToggle = toolbar.createDiv({ cls: "tmp-view-toggle" });
		(["grid", "list"] as ViewMode[]).forEach((mode) => {
			const btn = viewToggle.createEl("button", {
				cls: `tmp-pill ${mode === this.viewMode ? "tmp-pill-active" : ""}`,
				text: mode === "grid" ? "Grid" : "List",
			});
			btn.onclick = () => {
				this.viewMode = mode;
				this.render();
			};
		});

		const sorted = sortListings(listings, this.sortMode);
		const listContainer = container.createDiv({ cls: "tmp-section" });
		const openListing = (listing: Listing) => this.openListing(product.tmp_id, listing);
		if (this.viewMode === "grid") {
			renderListingGrid(listContainer, sorted, openListing);
		} else {
			renderListingTable(listContainer, sorted, openListing);
		}

		this.markNewAsSeen(product.tmp_id, search.id, listings);
	}

	private renderChart(container: HTMLElement, listings: Listing[]): void {
		const points = computePriceHistory(listings, this.period);
		const annotationValue = lowestInMonths(points, ANNOTATION_MONTHS);
		renderPriceChart(container, {
			points,
			period: this.period,
			onPeriodChange: (period) => {
				this.period = period;
				this.render();
			},
			annotation:
				annotationValue != null
					? { value: annotationValue, label: `Lowest in ${ANNOTATION_MONTHS}m: ${annotationValue.toFixed(0)}` }
					: null,
		});
	}

	private openListing(productId: string, listing: Listing): void {
		if (!listing.url) {
			new Notice("This listing has no source URL.");
			return;
		}
		window.open(listing.url, "_blank", "noopener");
	}

	/** is_new is GUI-owned per data-model.md: clear it on the daemon once the user has viewed this saved search. */
	private markNewAsSeen(productId: string, savedSearchId: string, listings: Listing[]): void {
		const key = `${productId}:${savedSearchId}`;
		if (this.markedSeenFor === key) return;
		this.markedSeenFor = key;

		const newOnes = listings.filter((l) => l.is_new);
		if (newOnes.length === 0) return;

		void (async () => {
			let daemonReachable = true;
			for (const listing of newOnes) {
				const result = await this.plugin.api.markListingSeen(productId, listing.id);
				if (!result.ok) {
					daemonReachable = false;
					break;
				}
			}
			if (!daemonReachable) {
				new Notice("Daemon offline — \"NEW\" badges will stay until it's back online.");
			}
		})();
	}
}
