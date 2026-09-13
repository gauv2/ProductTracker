import type { Platform, Product, SavedSearch } from "../types";

export interface SavedSearchFormValues {
	productName: string;
	label: string;
	platforms: Platform[];
	query: string;
	titleIncludes: string;
	excludeWords: string;
	minPrice: string;
	maxPrice: string;
	mpDistanceKm: string;
	mpPostcode: string;
}

export interface SavedSearchFormOptions {
	products: Product[];
	/** Preset platform selection driven by the Marktplaats/eBay/Both tab. */
	defaultPlatforms: Platform[];
	existing?: { product: Product; search: SavedSearch };
	onSubmit: (values: SavedSearchFormValues) => void | Promise<void>;
	onCancel?: () => void;
}

/**
 * Shared add/edit form for a saved search. The product field is a single
 * text input with a <datalist> of existing product names: typing an
 * existing name attaches the search to that product, typing a new one
 * creates the product first. This keeps "+ Add" a one-step action even
 * though a saved search technically nests under a product note.
 */
export function renderSavedSearchForm(container: HTMLElement, opts: SavedSearchFormOptions): void {
	container.empty();
	const form = container.createEl("form", { cls: "tmp-form" });
	form.onsubmit = async (e) => {
		e.preventDefault();
		await opts.onSubmit(readValues());
	};

	const existing = opts.existing;

	const productRow = form.createDiv({ cls: "tmp-form-row" });
	productRow.createEl("label", { text: "Product" });
	const productInput = productRow.createEl("input", {
		type: "text",
		attr: { list: "tmp-product-datalist", placeholder: "Existing or new product name" },
	}) as HTMLInputElement;
	productInput.value = existing?.product.name ?? "";
	const datalist = productRow.createEl("datalist", { attr: { id: "tmp-product-datalist" } });
	for (const p of opts.products) {
		datalist.createEl("option", { value: p.name });
	}

	const labelRow = form.createDiv({ cls: "tmp-form-row" });
	labelRow.createEl("label", { text: "Label" });
	const labelInput = labelRow.createEl("input", { type: "text", attr: { placeholder: "e.g. Nvidia DGX" } }) as HTMLInputElement;
	labelInput.value = existing?.search.label ?? "";

	const platformRow = form.createDiv({ cls: "tmp-form-row" });
	platformRow.createEl("label", { text: "Platforms" });
	const platformBox = platformRow.createDiv({ cls: "tmp-checkbox-group" });
	const platformChecks: Record<Platform, HTMLInputElement> = {} as Record<Platform, HTMLInputElement>;
	const initialPlatforms = existing?.search.platforms ?? opts.defaultPlatforms;
	(["marktplaats", "ebay", "facebook"] as Platform[]).forEach((platform) => {
		const wrap = platformBox.createEl("label", { cls: "tmp-checkbox" });
		const cb = wrap.createEl("input", { type: "checkbox" }) as HTMLInputElement;
		cb.checked = initialPlatforms.includes(platform);
		wrap.createSpan({ text: platform === "marktplaats" ? "Marktplaats" : platform === "ebay" ? "eBay" : "Facebook" });
		platformChecks[platform] = cb;
	});

	const queryRow = form.createDiv({ cls: "tmp-form-row" });
	queryRow.createEl("label", { text: "Query" });
	const queryInput = queryRow.createEl("input", { type: "text", attr: { required: "true" } }) as HTMLInputElement;
	queryInput.value = existing?.search.query ?? "";

	const includesRow = form.createDiv({ cls: "tmp-form-row" });
	includesRow.createEl("label", { text: "Title must include" });
	const includesInput = includesRow.createEl("input", {
		type: "text",
		attr: { placeholder: "comma, separated, terms" },
	}) as HTMLInputElement;
	includesInput.value = (existing?.search.title_includes ?? []).join(", ");

	const excludeRow = form.createDiv({ cls: "tmp-form-row" });
	excludeRow.createEl("label", { text: "Exclude words" });
	const excludeInput = excludeRow.createEl("input", {
		type: "text",
		attr: { placeholder: "comma, separated, words" },
	}) as HTMLInputElement;
	excludeInput.value = (existing?.search.exclude_words ?? []).join(", ");

	const priceRow = form.createDiv({ cls: "tmp-form-row tmp-form-row-split" });
	const minWrap = priceRow.createDiv();
	minWrap.createEl("label", { text: "Min price" });
	const minInput = minWrap.createEl("input", { type: "number", attr: { step: "0.01" } }) as HTMLInputElement;
	minInput.value = existing?.search.min_price != null ? String(existing.search.min_price) : "";
	const maxWrap = priceRow.createDiv();
	maxWrap.createEl("label", { text: "Max price" });
	const maxInput = maxWrap.createEl("input", { type: "number", attr: { step: "0.01" } }) as HTMLInputElement;
	maxInput.value = existing?.search.max_price != null ? String(existing.search.max_price) : "";

	const mpRow = form.createDiv({ cls: "tmp-form-row tmp-form-row-split" });
	const distWrap = mpRow.createDiv();
	distWrap.createEl("label", { text: "Distance (km, Marktplaats)" });
	const distInput = distWrap.createEl("input", { type: "number", attr: { step: "1" } }) as HTMLInputElement;
	distInput.value = existing?.search.mp_distance_km != null ? String(existing.search.mp_distance_km) : "";
	const postcodeWrap = mpRow.createDiv();
	postcodeWrap.createEl("label", { text: "Postcode (Marktplaats)" });
	const postcodeInput = postcodeWrap.createEl("input", { type: "text" }) as HTMLInputElement;
	postcodeInput.value = existing?.search.mp_postcode ?? "";

	const buttonRow = form.createDiv({ cls: "tmp-form-row tmp-form-buttons" });
	buttonRow.createEl("button", { type: "submit", cls: "mod-cta", text: existing ? "Save changes" : "+ Add" });
	if (opts.onCancel) {
		const cancelBtn = buttonRow.createEl("button", { type: "button", text: "Cancel" });
		cancelBtn.onclick = () => opts.onCancel?.();
	}

	function readValues(): SavedSearchFormValues {
		return {
			productName: productInput.value.trim(),
			label: labelInput.value.trim(),
			platforms: (Object.keys(platformChecks) as Platform[]).filter((p) => platformChecks[p].checked),
			query: queryInput.value.trim(),
			titleIncludes: includesInput.value.trim(),
			excludeWords: excludeInput.value.trim(),
			minPrice: minInput.value.trim(),
			maxPrice: maxInput.value.trim(),
			mpDistanceKm: distInput.value.trim(),
			mpPostcode: postcodeInput.value.trim(),
		};
	}
}

export function parseCommaList(value: string): string[] {
	return value
		.split(",")
		.map((s) => s.trim())
		.filter((s) => s.length > 0);
}

export function parseOptionalNumber(value: string): number | null {
	if (value.trim().length === 0) return null;
	const n = Number(value);
	return Number.isNaN(n) ? null : n;
}
