import { Plugin, WorkspaceLeaf } from "obsidian";
import { DaemonApiClient } from "./lib/api-client";
import { VaultDataSource } from "./lib/vault-data";
import { DEFAULT_SETTINGS, TrackMyProductSettings, TrackMyProductSettingTab } from "./settings";
import { MarketplaceView, VIEW_TYPE_MARKETPLACE } from "./views/marketplace-view";
import { ListingsView, VIEW_TYPE_LISTINGS } from "./views/listings-view";

export default class TrackMyProductPlugin extends Plugin {
	settings: TrackMyProductSettings = DEFAULT_SETTINGS;
	vaultData!: VaultDataSource;
	api!: DaemonApiClient;

	async onload(): Promise<void> {
		await this.loadSettings();

		this.vaultData = new VaultDataSource(this.app, () => this.settings.productsFolder);
		this.api = new DaemonApiClient(() => this.settings.daemonBaseUrl);

		this.registerView(VIEW_TYPE_MARKETPLACE, (leaf) => new MarketplaceView(leaf, this));
		this.registerView(VIEW_TYPE_LISTINGS, (leaf) => new ListingsView(leaf, this));

		this.addRibbonIcon("shopping-cart", "Open TrackMyProduct marketplace", () => {
			void this.activateMarketplaceView();
		});

		this.addCommand({
			id: "open-marketplace-view",
			name: "Open marketplace view",
			callback: () => void this.activateMarketplaceView(),
		});

		this.addSettingTab(new TrackMyProductSettingTab(this.app, this));
	}

	onunload(): void {
		// Views are torn down by Obsidian's workspace; nothing else to clean up.
	}

	private async activateMarketplaceView(): Promise<void> {
		const existing = this.app.workspace.getLeavesOfType(VIEW_TYPE_MARKETPLACE);
		let leaf: WorkspaceLeaf;
		if (existing.length > 0) {
			leaf = existing[0];
		} else {
			leaf = this.app.workspace.getLeaf(true);
			await leaf.setViewState({ type: VIEW_TYPE_MARKETPLACE, active: true });
		}
		this.app.workspace.revealLeaf(leaf);
	}

	async loadSettings(): Promise<void> {
		this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
	}

	async saveSettings(): Promise<void> {
		await this.saveData(this.settings);
	}
}
