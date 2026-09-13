import type { Listing, Period, PriceHistoryPoint } from "../types";

/**
 * docs/data-model.md is explicit that price history is *derived*, not
 * stored: "compute it from listings[] grouped by day (or week for long
 * ranges) at read time, in whichever side renders the chart." Computing it
 * here (instead of calling the daemon's /price-history endpoint) is what
 * lets the chart render with the daemon offline.
 */
const PERIOD_DAYS: Record<Period, number | null> = {
	"1m": 30,
	"3m": 90,
	"6m": 182,
	year: 365,
	all: null,
};

export function computePriceHistory(listings: Listing[], period: Period): PriceHistoryPoint[] {
	const days = PERIOD_DAYS[period];
	const now = Date.now();
	const cutoff = days != null ? now - days * 24 * 60 * 60 * 1000 : -Infinity;

	const inRange = listings.filter((l) => {
		const t = Date.parse(l.posted_at);
		return !Number.isNaN(t) && t >= cutoff;
	});

	if (inRange.length === 0) return [];

	// Use daily buckets for anything up to a year, weekly buckets for "all"
	// when the span is long, per the data-model.md guidance.
	const useWeekly = period === "all" && spanDays(inRange) > 400;
	const buckets = new Map<string, number[]>();

	for (const listing of inRange) {
		const key = useWeekly ? weekKey(listing.posted_at) : dayKey(listing.posted_at);
		if (!key) continue;
		const arr = buckets.get(key) ?? [];
		arr.push(listing.price);
		buckets.set(key, arr);
	}

	return Array.from(buckets.entries())
		.map(([date, prices]) => ({
			date,
			min: Math.min(...prices),
			avg: prices.reduce((a, b) => a + b, 0) / prices.length,
		}))
		.sort((a, b) => (a.date < b.date ? -1 : a.date > b.date ? 1 : 0));
}

/** Lowest `min` point within the last N months, for the dashed annotation line. */
export function lowestInMonths(points: PriceHistoryPoint[], months: number): number | null {
	if (points.length === 0) return null;
	const cutoff = Date.now() - months * 30 * 24 * 60 * 60 * 1000;
	const relevant = points.filter((p) => {
		const t = Date.parse(p.date);
		return Number.isNaN(t) || t >= cutoff;
	});
	const source = relevant.length > 0 ? relevant : points;
	return Math.min(...source.map((p) => p.min));
}

function spanDays(listings: Listing[]): number {
	const times = listings.map((l) => Date.parse(l.posted_at)).filter((t) => !Number.isNaN(t));
	if (times.length === 0) return 0;
	return (Math.max(...times) - Math.min(...times)) / (24 * 60 * 60 * 1000);
}

function dayKey(iso: string): string | null {
	const t = Date.parse(iso);
	if (Number.isNaN(t)) return null;
	return new Date(t).toISOString().slice(0, 10);
}

function weekKey(iso: string): string | null {
	const t = Date.parse(iso);
	if (Number.isNaN(t)) return null;
	const d = new Date(t);
	// ISO week start (Monday)
	const day = (d.getUTCDay() + 6) % 7;
	d.setUTCDate(d.getUTCDate() - day);
	return d.toISOString().slice(0, 10);
}
