import type { Period, SavedSearch, SortMode } from "../types";

export type ApiResult<T> = { ok: true; data: T } | { ok: false; error: string };

/**
 * Thin client for the daemon's local API (docs/api-contract.md). Every call
 * degrades gracefully: network failures (daemon not running) and non-2xx
 * responses both resolve to `{ ok: false, error }` rather than throwing, so
 * callers can render an inline message instead of crashing the view.
 */
export class DaemonApiClient {
	constructor(private getBaseUrl: () => string) {}

	async health(): Promise<ApiResult<{ status: string; daemon_version: string; last_scan_cycle_at: string | null }>> {
		return this.request("GET", "/health");
	}

	async listProducts(): Promise<ApiResult<unknown>> {
		return this.request("GET", "/products");
	}

	async createProduct(data: { name: string; category?: string }): Promise<ApiResult<{ tmp_id: string }>> {
		return this.request("POST", "/products", data);
	}

	async patchProduct(productId: string, data: Partial<{ name: string; category: string }>): Promise<ApiResult<unknown>> {
		return this.request("PATCH", `/products/${encodeURIComponent(productId)}`, data);
	}

	async deleteProduct(productId: string): Promise<ApiResult<unknown>> {
		return this.request("DELETE", `/products/${encodeURIComponent(productId)}`);
	}

	async addSavedSearch(
		productId: string,
		data: Omit<SavedSearch, "id" | "enabled" | "last_scanned_at">
	): Promise<ApiResult<SavedSearch>> {
		return this.request("POST", `/products/${encodeURIComponent(productId)}/saved-searches`, data);
	}

	async patchSavedSearch(
		productId: string,
		savedSearchId: string,
		data: Partial<SavedSearch>
	): Promise<ApiResult<SavedSearch>> {
		return this.request(
			"PATCH",
			`/products/${encodeURIComponent(productId)}/saved-searches/${encodeURIComponent(savedSearchId)}`,
			data
		);
	}

	async deleteSavedSearch(productId: string, savedSearchId: string): Promise<ApiResult<unknown>> {
		return this.request(
			"DELETE",
			`/products/${encodeURIComponent(productId)}/saved-searches/${encodeURIComponent(savedSearchId)}`
		);
	}

	async triggerScan(productId: string, savedSearchId: string): Promise<ApiResult<unknown>> {
		return this.request(
			"POST",
			`/products/${encodeURIComponent(productId)}/saved-searches/${encodeURIComponent(savedSearchId)}/scan`
		);
	}

	async getListings(
		productId: string,
		opts: { sort?: SortMode; savedSearchId?: string } = {}
	): Promise<ApiResult<unknown>> {
		const params = new URLSearchParams();
		if (opts.sort) params.set("sort", opts.sort);
		if (opts.savedSearchId) params.set("saved_search_id", opts.savedSearchId);
		const qs = params.toString();
		return this.request("GET", `/products/${encodeURIComponent(productId)}/listings${qs ? `?${qs}` : ""}`);
	}

	async markListingSeen(productId: string, listingId: string): Promise<ApiResult<unknown>> {
		return this.request(
			"PATCH",
			`/products/${encodeURIComponent(productId)}/listings/${encodeURIComponent(listingId)}`,
			{ is_new: false }
		);
	}

	async deleteListing(productId: string, listingId: string): Promise<ApiResult<unknown>> {
		return this.request(
			"DELETE",
			`/products/${encodeURIComponent(productId)}/listings/${encodeURIComponent(listingId)}`
		);
	}

	async getPriceHistory(productId: string, period: Period): Promise<ApiResult<{ points: { date: string; min: number; avg: number }[] }>> {
		return this.request("GET", `/products/${encodeURIComponent(productId)}/price-history?period=${period}`);
	}

	async refreshNewPrice(productId: string): Promise<ApiResult<unknown>> {
		return this.request("POST", `/products/${encodeURIComponent(productId)}/refresh-new-price`);
	}

	private async request<T>(method: string, path: string, body?: unknown): Promise<ApiResult<T>> {
		const base = this.getBaseUrl();
		try {
			const res = await fetch(`${base}${path}`, {
				method,
				headers: body !== undefined ? { "Content-Type": "application/json" } : undefined,
				body: body !== undefined ? JSON.stringify(body) : undefined,
			});

			if (!res.ok) {
				const message = await extractErrorMessage(res);
				return { ok: false, error: message };
			}

			if (res.status === 204) {
				return { ok: true, data: undefined as T };
			}

			const data = (await res.json()) as T;
			return { ok: true, data };
		} catch (err) {
			return {
				ok: false,
				error: `Could not reach the TrackMyProduct daemon at ${base}. Is it running? (${describeError(err)})`,
			};
		}
	}
}

async function extractErrorMessage(res: Response): Promise<string> {
	try {
		const body = (await res.json()) as { error?: { message?: string; code?: string } };
		if (body?.error?.message) return body.error.message;
	} catch {
		// fall through to status text
	}
	return `${res.status} ${res.statusText}`;
}

function describeError(err: unknown): string {
	if (err instanceof Error) return err.message;
	return String(err);
}
