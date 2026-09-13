import type { Platform } from "../types";

export const PLATFORM_LABEL: Record<Platform, string> = {
	marktplaats: "Marktplaats",
	ebay: "eBay",
	facebook: "Facebook",
};

export function formatPrice(price: number, currency = "EUR"): string {
	try {
		return new Intl.NumberFormat("nl-NL", { style: "currency", currency }).format(price);
	} catch {
		return `€${price.toFixed(2)}`;
	}
}

export function formatDistance(km: number | null): string {
	if (km == null) return "—";
	return km < 1 ? `${Math.round(km * 1000)} m` : `${km.toFixed(1)} km`;
}

export function formatDateTime(iso: string | null): string {
	if (!iso) return "—";
	const d = new Date(iso);
	if (Number.isNaN(d.getTime())) return iso;
	return d.toLocaleString("en-GB", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
}

export function formatDate(iso: string | null): string {
	if (!iso) return "—";
	const d = new Date(iso);
	if (Number.isNaN(d.getTime())) return iso;
	return d.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
}

export function formatRelative(iso: string | null): string {
	if (!iso) return "never";
	const t = Date.parse(iso);
	if (Number.isNaN(t)) return iso;
	const diffMs = Date.now() - t;
	const minutes = Math.round(diffMs / 60000);
	if (minutes < 1) return "just now";
	if (minutes < 60) return `${minutes}m ago`;
	const hours = Math.round(minutes / 60);
	if (hours < 24) return `${hours}h ago`;
	const days = Math.round(hours / 24);
	return `${days}d ago`;
}
