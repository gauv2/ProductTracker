import { App, TFile } from "obsidian";
import type {
	Listing,
	NewPrice,
	NotificationSent,
	Product,
	ProductStats,
	SavedSearch,
	StatEntry,
} from "../types";

/**
 * Read-only vault access. Every product note under the configured products
 * folder is parsed via Obsidian's own MetadataCache (which already parses
 * YAML frontmatter for us) — no Node file I/O, no bundled YAML parser.
 *
 * This must keep working with the daemon completely offline: it never makes
 * a network call.
 */
export class VaultDataSource {
	constructor(
		private app: App,
		private getProductsFolder: () => string
	) {}

	/** All product notes under the configured folder, best-effort parsed. */
	listProducts(): Product[] {
		const folder = normalizeFolder(this.getProductsFolder());
		const products: Product[] = [];

		for (const file of this.app.vault.getMarkdownFiles()) {
			if (!isInFolder(file, folder)) continue;
			const product = this.readProduct(file);
			if (product) products.push(product);
		}

		return products.sort((a, b) => a.name.localeCompare(b.name));
	}

	getProductById(tmpId: string): Product | null {
		return this.listProducts().find((p) => p.tmp_id === tmpId) ?? null;
	}

	getFileForProduct(tmpId: string): TFile | null {
		const folder = normalizeFolder(this.getProductsFolder());
		for (const file of this.app.vault.getMarkdownFiles()) {
			if (!isInFolder(file, folder)) continue;
			const cache = this.app.metadataCache.getFileCache(file);
			if (cache?.frontmatter?.tmp_id === tmpId) return file;
		}
		return null;
	}

	private readProduct(file: TFile): Product | null {
		const cache = this.app.metadataCache.getFileCache(file);
		const fm = cache?.frontmatter;
		if (!fm || fm.tmp_type !== "product") return null;

		return {
			tmp_id: String(fm.tmp_id ?? file.basename),
			tmp_type: "product",
			name: String(fm.name ?? file.basename),
			category: String(fm.category ?? ""),
			created_at: String(fm.created_at ?? ""),
			updated_at: String(fm.updated_at ?? ""),
			saved_searches: parseSavedSearches(fm.saved_searches),
			listings: parseListings(fm.listings),
			stats: parseStats(fm.stats),
			new_price: parseNewPrice(fm.new_price),
			notifications_sent: parseNotifications(fm.notifications_sent),
			filePath: file.path,
		};
	}
}

function normalizeFolder(folder: string): string {
	const trimmed = folder.trim().replace(/^\/+/, "").replace(/\/+$/, "");
	return trimmed;
}

function isInFolder(file: TFile, folder: string): boolean {
	if (!folder) return true;
	return file.path === folder || file.path.startsWith(`${folder}/`);
}

function asArray(value: unknown): unknown[] {
	return Array.isArray(value) ? value : [];
}

function asStringArray(value: unknown): string[] {
	return asArray(value).map((v) => String(v));
}

function asPlatforms(value: unknown): SavedSearch["platforms"] {
	return asArray(value).filter(
		(v): v is SavedSearch["platforms"][number] =>
			v === "marktplaats" || v === "ebay" || v === "facebook"
	);
}

function asNumberOrNull(value: unknown): number | null {
	return typeof value === "number" ? value : null;
}

function asStringOrNull(value: unknown): string | null {
	return typeof value === "string" ? value : null;
}

function parseSavedSearches(value: unknown): SavedSearch[] {
	return asArray(value).map((raw) => {
		const s = (raw ?? {}) as Record<string, unknown>;
		return {
			id: String(s.id ?? ""),
			label: String(s.label ?? ""),
			platforms: asPlatforms(s.platforms),
			query: String(s.query ?? ""),
			title_includes: asStringArray(s.title_includes),
			exclude_words: asStringArray(s.exclude_words),
			min_price: asNumberOrNull(s.min_price),
			max_price: asNumberOrNull(s.max_price),
			mp_distance_km: asNumberOrNull(s.mp_distance_km),
			mp_postcode: asStringOrNull(s.mp_postcode),
			enabled: Boolean(s.enabled),
			last_scanned_at: asStringOrNull(s.last_scanned_at),
		};
	});
}

function parseListings(value: unknown): Listing[] {
	return asArray(value).map((raw) => {
		const l = (raw ?? {}) as Record<string, unknown>;
		return {
			id: String(l.id ?? ""),
			saved_search_id: String(l.saved_search_id ?? ""),
			platform: (l.platform as Listing["platform"]) ?? "marktplaats",
			title: String(l.title ?? ""),
			price: typeof l.price === "number" ? l.price : 0,
			currency: String(l.currency ?? "EUR"),
			location: String(l.location ?? ""),
			distance_km: asNumberOrNull(l.distance_km),
			posted_at: String(l.posted_at ?? ""),
			seen_at: String(l.seen_at ?? ""),
			url: String(l.url ?? ""),
			is_new: Boolean(l.is_new),
		};
	});
}

function parseStatEntry(value: unknown): StatEntry | null {
	if (!value || typeof value !== "object") return null;
	const s = value as Record<string, unknown>;
	if (typeof s.price !== "number") return null;
	return {
		price: s.price,
		listing_id: String(s.listing_id ?? ""),
		at: String(s.at ?? ""),
	};
}

function parseStats(value: unknown): ProductStats {
	const s = (value ?? {}) as Record<string, unknown>;
	return {
		all_time_high: parseStatEntry(s.all_time_high),
		all_time_low: parseStatEntry(s.all_time_low),
	};
}

function parseNewPrice(value: unknown): NewPrice {
	const n = (value ?? {}) as Record<string, unknown>;
	const source = n.source === "google" || n.source === "tweakers" ? n.source : null;
	return {
		price: asNumberOrNull(n.price),
		currency: String(n.currency ?? "EUR"),
		source,
		source_url: asStringOrNull(n.source_url),
		fetched_at: asStringOrNull(n.fetched_at),
	};
}

function parseNotifications(value: unknown): NotificationSent[] {
	return asArray(value).map((raw) => {
		const n = (raw ?? {}) as Record<string, unknown>;
		return { key: String(n.key ?? ""), sent_at: String(n.sent_at ?? "") };
	});
}
