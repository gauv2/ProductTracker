// Mirrors the frontmatter schema frozen in docs/data-model.md. Keep in sync
// with that file — it is the contract between the daemon and this GUI.

export type Platform = "marktplaats" | "ebay" | "facebook";

export type SortMode = "newest" | "cheapest" | "nearest" | "best";

export type ViewMode = "grid" | "list";

export type Period = "1m" | "3m" | "6m" | "year" | "all";

export interface SavedSearch {
	id: string;
	label: string;
	platforms: Platform[];
	query: string;
	title_includes: string[];
	exclude_words: string[];
	min_price: number | null;
	max_price: number | null;
	mp_distance_km: number | null;
	mp_postcode: string | null;
	enabled: boolean;
	last_scanned_at: string | null;
}

export interface Listing {
	id: string;
	saved_search_id: string;
	platform: Platform;
	title: string;
	price: number;
	currency: string;
	location: string;
	distance_km: number | null;
	posted_at: string;
	seen_at: string;
	url: string;
	is_new: boolean;
}

export interface StatEntry {
	price: number;
	listing_id: string;
	at: string;
}

export interface ProductStats {
	all_time_high: StatEntry | null;
	all_time_low: StatEntry | null;
}

export interface NewPrice {
	price: number | null;
	currency: string;
	source: "google" | "tweakers" | null;
	source_url: string | null;
	fetched_at: string | null;
}

export interface NotificationSent {
	key: string;
	sent_at: string;
}

export interface Product {
	tmp_id: string;
	tmp_type: "product";
	name: string;
	category: string;
	created_at: string;
	updated_at: string;
	saved_searches: SavedSearch[];
	listings: Listing[];
	stats: ProductStats;
	new_price: NewPrice;
	notifications_sent: NotificationSent[];
	/** Vault-relative path of the note this was read from. Not part of the frontmatter contract. */
	filePath: string;
}

export interface PriceHistoryPoint {
	date: string;
	min: number;
	avg: number;
}
