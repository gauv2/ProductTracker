import { App, PluginSettingTab, Setting } from "obsidian";
import type TrackMyProductPlugin from "./main";

export interface TrackMyProductSettings {
	productsFolder: string;
	daemonBaseUrl: string;
}

export const DEFAULT_SETTINGS: TrackMyProductSettings = {
	productsFolder: "TrackMyProduct/",
	daemonBaseUrl: "http://127.0.0.1:8756",
};

export class TrackMyProductSettingTab extends PluginSettingTab {
	plugin: TrackMyProductPlugin;

	constructor(app: App, plugin: TrackMyProductPlugin) {
		super(app, plugin);
		this.plugin = plugin;
	}

	display(): void {
		const { containerEl } = this;
		containerEl.empty();

		containerEl.createEl("h2", { text: "TrackMyProduct" });

		new Setting(containerEl)
			.setName("Products folder")
			.setDesc(
				"Vault folder that holds one note per tracked product (frontmatter schema in docs/data-model.md)."
			)
			.addText((text) =>
				text
					.setPlaceholder("TrackMyProduct/")
					.setValue(this.plugin.settings.productsFolder)
					.onChange(async (value) => {
						const normalized = value.trim().length > 0 ? value.trim() : DEFAULT_SETTINGS.productsFolder;
						this.plugin.settings.productsFolder = normalized.endsWith("/")
							? normalized
							: `${normalized}/`;
						await this.plugin.saveSettings();
					})
			);

		new Setting(containerEl)
			.setName("Daemon API base URL")
			.setDesc(
				"Local TrackMyProduct daemon used for saved-search / scan / listing mutations. Browsing the vault works without it."
			)
			.addText((text) =>
				text
					.setPlaceholder(DEFAULT_SETTINGS.daemonBaseUrl)
					.setValue(this.plugin.settings.daemonBaseUrl)
					.onChange(async (value) => {
						const normalized = value.trim().length > 0 ? value.trim() : DEFAULT_SETTINGS.daemonBaseUrl;
						this.plugin.settings.daemonBaseUrl = normalized.replace(/\/+$/, "");
						await this.plugin.saveSettings();
					})
			);
	}
}
