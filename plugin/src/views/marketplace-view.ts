import { ItemView, Notice, WorkspaceLeaf } from "obsidian";
import type TrackMyProductPlugin from "../main";
import type { Platform, Product, SavedSearch } from "../types";
import { renderSavedSearchCard } from "../components/saved-search-card";
import {
	parseCommaList,
	parseOptionalNumber,
	renderSavedSearchForm,
	SavedSearchFormValues,
} from "../components/saved-search-form";
import { VIEW_TYPE_LISTINGS } from "./listings-view";

export const VIEW_TYPE_MARKETPLACE = "trackmyproduct-marketplace";

type PlatformTab = "marktplaats" | "ebay" | "both";

const TAB_PLATFORMS: Record<PlatformTab, Platform[]> = {
	marktplaats: ["marktplaats"],
	ebay: ["ebay"],
	both: ["marktplaats", "ebay"],
};

export class MarketplaceView extends ItemView {
	private plugin: TrackMyProductPlugin;
	private activeTab: PlatformTab = "both";
	private formOpen = false;
	private editingSearch: { product: Product; search: SavedSearch } | null = null;
	private statusEl!: HTMLElement;
	private bodyEl!: HTMLElement;

	constructor(leaf: WorkspaceLeaf, plugin: TrackMyProductPlugin) {
		super(leaf);
		this.plugin = plugin;
	}

	getViewType(): string {
		return VIEW_TYPE_MARKETPLACE;
	}

	getDisplayText(): string {
		return "Marketplace";
	}

	getIcon(): string {
		return "shopping-cart";
	}

	async onOpen(): Promise<void> {
		this.render();
		this.registerEvent(this.app.metadataCache.on("changed", () => this.render()));
	}

	private render(): void {
		const container = this.containerEl.children[1] as HTMLElement;
		container.empty();
		container.addClass("tmp-view");

		const header = container.createDiv({ cls: "tmp-header" });
		header.createEl("h2", { text: "Marketplace" });
		this.statusEl = header.createDiv({ cls: "tmp-daemon-status" });
		void this.refreshDaemonStatus();

		const tabRow = container.createDiv({ cls: "tmp-tabs" });
		(Object.keys(TAB_PLATFORMS) as PlatformTab[]).forEach((tab) => {
			const btn = tabRow.createEl("button", {
				cls: `tmp-pill ${tab === this.activeTab ? "tmp-pill-active" : ""}`,
				text: tab === "marktplaats" ? "Marktplaats" : tab === "ebay" ? "eBay" : "Both",
			});
			btn.onclick = () => {
				this.activeTab = tab;
				this.render();
			};
		});

		const addBar = container.createDiv({ cls: "tmp-add-bar" });
		const addBtn = addBar.createEl("button", { cls: "mod-cta", text: this.formOpen ? "− Close" : "+ Add" });
		addBtn.onclick = () => {
			this.formOpen = !this.formOpen;
			this.editingSearch = null;
			this.render();
		};

		if (this.formOpen || this.editingSearch) {
			const formContainer = container.createDiv({ cls: "tmp-form-container" });
			renderSavedSearchForm(formContainer, {
				products: this.plugin.vaultData.listProducts(),
				defaultPlatforms: TAB_PLATFORMS[this.activeTab],
				existing: this.editingSearch ?? undefined,
				onSubmit: (values) => this.handleFormSubmit(values),
				onCancel: () => {
					this.formOpen = false;
					this.editingSearch = null;
					this.render();
				},
			});
		}

		this.bodyEl = container.createDiv({ cls: "tmp-card-list" });
		this.renderCards();
	}

	private renderCards(): void {
		this.bodyEl.empty();
		const products = this.plugin.vaultData.listProducts();
		const pairs: { product: Product; search: SavedSearch }[] = [];
		for (const product of products) {
			for (const search of product.saved_searches) {
				pairs.push({ product, search });
			}
		}

		if (pairs.length === 0) {
			this.bodyEl.createDiv({
				cls: "tmp-empty-state",
				text: `No saved searches yet. Add one above, or check that "${this.plugin.settings.productsFolder}" is the right vault folder in settings.`,
			});
			return;
		}

		for (const { product, search } of pairs) {
			renderSavedSearchCard(this.bodyEl, product, search, {
				onOpen: (p, s) => this.openListings(p, s),
				onRefresh: (p, s) => this.handleRefresh(p, s),
				onEdit: (p, s) => {
					this.editingSearch = { product: p, search: s };
					this.formOpen = false;
					this.render();
				},
				onDelete: (p, s) => this.handleDelete(p, s),
				onToggle: (p, s) => this.handleToggle(p, s),
			});
		}
	}

	private async openListings(product: Product, search: SavedSearch): Promise<void> {
		const leaf = this.app.workspace.getLeaf(true);
		await leaf.setViewState({
			type: VIEW_TYPE_LISTINGS,
			active: true,
			state: { productId: product.tmp_id, savedSearchId: search.id },
		});
		this.app.workspace.revealLeaf(leaf);
	}

	private async handleFormSubmit(values: SavedSearchFormValues): Promise<void> {
		if (!values.productName) {
			new Notice("Product name is required.");
			return;
		}
		if (!values.query) {
			new Notice("Query is required.");
			return;
		}
		if (values.platforms.length === 0) {
			new Notice("Pick at least one platform.");
			return;
		}

		const editing = this.editingSearch;
		let productId = editing?.product.tmp_id ?? null;

		if (!productId) {
			const existingProduct = this.plugin.vaultData
				.listProducts()
				.find((p) => p.name.toLowerCase() === values.productName.toLowerCase());
			if (existingProduct) {
				productId = existingProduct.tmp_id;
			} else {
				const created = await this.plugin.api.createProduct({ name: values.productName });
				if (!created.ok) {
					new Notice(`Could not create product: ${created.error}`);
					return;
				}
				productId = created.data.tmp_id;
			}
		}

		const payload = {
			label: values.label || values.query,
			platforms: values.platforms,
			query: values.query,
			title_includes: parseCommaList(values.titleIncludes),
			exclude_words: parseCommaList(values.excludeWords),
			min_price: parseOptionalNumber(values.minPrice),
			max_price: parseOptionalNumber(values.maxPrice),
			mp_distance_km: parseOptionalNumber(values.mpDistanceKm),
			mp_postcode: values.mpPostcode || null,
		};

		const result = editing
			? await this.plugin.api.patchSavedSearch(productId, editing.search.id, payload)
			: await this.plugin.api.addSavedSearch(productId, payload);

		if (!result.ok) {
			new Notice(`Could not save: ${result.error}`);
			return;
		}

		new Notice(editing ? "Saved search updated." : "Saved search added.");
		this.formOpen = false;
		this.editingSearch = null;
		this.render();
	}

	private async handleRefresh(product: Product, search: SavedSearch): Promise<void> {
		const result = await this.plugin.api.triggerScan(product.tmp_id, search.id);
		new Notice(result.ok ? `Scanning "${search.label}"…` : `Could not trigger scan: ${result.error}`);
	}

	private async handleToggle(product: Product, search: SavedSearch): Promise<void> {
		const result = await this.plugin.api.patchSavedSearch(product.tmp_id, search.id, { enabled: !search.enabled });
		if (!result.ok) {
			new Notice(`Could not update: ${result.error}`);
			return;
		}
		this.render();
	}

	private async handleDelete(product: Product, search: SavedSearch): Promise<void> {
		const result = await this.plugin.api.deleteSavedSearch(product.tmp_id, search.id);
		if (!result.ok) {
			new Notice(`Could not delete: ${result.error}`);
			return;
		}
		new Notice("Saved search deleted.");
		this.render();
	}

	private async refreshDaemonStatus(): Promise<void> {
		const result = await this.plugin.api.health();
		this.statusEl.empty();
		if (result.ok) {
			this.statusEl.createSpan({ cls: "tmp-status-ok", text: `Daemon online (v${result.data.daemon_version})` });
		} else {
			this.statusEl.createSpan({ cls: "tmp-status-offline", text: "Daemon offline — browsing only" });
		}
	}
}
