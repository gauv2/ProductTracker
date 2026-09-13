import type { Listing, SortMode } from "../types";

/**
 * "Best" has no single obvious definition in the contract — judgment call
 * (documented in plugin/README.md): normalize price and distance to 0..1
 * within the current result set and blend them, weighting price higher.
 * Listings missing distance (e.g. eBay) fall back to a price-only score.
 */
const BEST_PRICE_WEIGHT = 0.65;
const BEST_DISTANCE_WEIGHT = 0.35;

export function sortListings(listings: Listing[], mode: SortMode): Listing[] {
	const copy = [...listings];

	switch (mode) {
		case "newest":
			return copy.sort((a, b) => timeValue(b.posted_at) - timeValue(a.posted_at));
		case "cheapest":
			return copy.sort((a, b) => a.price - b.price);
		case "nearest":
			return copy.sort((a, b) => distanceValue(a) - distanceValue(b));
		case "best":
			return sortByBestScore(copy);
		default:
			return copy;
	}
}

function timeValue(iso: string): number {
	const t = Date.parse(iso);
	return Number.isNaN(t) ? 0 : t;
}

function distanceValue(listing: Listing): number {
	return listing.distance_km ?? Number.POSITIVE_INFINITY;
}

function sortByBestScore(listings: Listing[]): Listing[] {
	const prices = listings.map((l) => l.price);
	const distances = listings.filter((l) => l.distance_km != null).map((l) => l.distance_km as number);
	const hasDistances = distances.length > 0;

	const minPrice = Math.min(...prices);
	const maxPrice = Math.max(...prices);
	const minDist = hasDistances ? Math.min(...distances) : 0;
	const maxDist = hasDistances ? Math.max(...distances) : 0;

	const score = (l: Listing): number => {
		const priceNorm = normalize(l.price, minPrice, maxPrice);
		if (!hasDistances || l.distance_km == null) return priceNorm;
		const distNorm = normalize(l.distance_km, minDist, maxDist);
		return priceNorm * BEST_PRICE_WEIGHT + distNorm * BEST_DISTANCE_WEIGHT;
	};

	return listings
		.map((l) => ({ l, s: score(l) }))
		.sort((a, b) => a.s - b.s)
		.map((x) => x.l);
}

function normalize(value: number, min: number, max: number): number {
	if (max === min) return 0;
	return (value - min) / (max - min);
}
