import type { Period, PriceHistoryPoint } from "../types";

const SVG_NS = "http://www.w3.org/2000/svg";
const PERIODS: { key: Period; label: string }[] = [
	{ key: "1m", label: "1m" },
	{ key: "3m", label: "3m" },
	{ key: "6m", label: "6m" },
	{ key: "year", label: "Jaar" },
	{ key: "all", label: "Alles" },
];

export interface PriceChartOptions {
	points: PriceHistoryPoint[];
	period: Period;
	onPeriodChange: (period: Period) => void;
	annotation?: { value: number; label: string } | null;
	currency?: string;
}

/**
 * Hand-rolled inline SVG line chart — no bundled charting dependency. Kept
 * deliberately small: two series (min/avg), a euro axis, month ticks and one
 * dashed annotation line, which is everything the brief's mockups call for.
 */
export function renderPriceChart(container: HTMLElement, opts: PriceChartOptions): void {
	container.empty();
	container.addClass("tmp-price-chart");

	const periodRow = container.createDiv({ cls: "tmp-chart-periods" });
	for (const p of PERIODS) {
		const btn = periodRow.createEl("button", {
			text: p.label,
			cls: `tmp-pill ${p.key === opts.period ? "tmp-pill-active" : ""}`,
		});
		btn.onclick = () => opts.onPeriodChange(p.key);
	}

	const legend = container.createDiv({ cls: "tmp-chart-legend" });
	legend.createSpan({ cls: "tmp-legend-item tmp-legend-min", text: "Minimum" });
	legend.createSpan({ cls: "tmp-legend-item tmp-legend-avg", text: "Gemiddelde" });

	if (opts.points.length === 0) {
		container.createDiv({
			cls: "tmp-chart-empty",
			text: "Not enough listings yet for a price history chart.",
		});
		return;
	}

	const currency = opts.currency ?? "EUR";
	const width = 640;
	const height = 260;
	const padding = { top: 16, right: 16, bottom: 28, left: 56 };
	const plotW = width - padding.left - padding.right;
	const plotH = height - padding.top - padding.bottom;

	const values = opts.points.flatMap((p) => [p.min, p.avg]);
	if (opts.annotation) values.push(opts.annotation.value);
	let yMin = Math.min(...values);
	let yMax = Math.max(...values);
	if (yMin === yMax) {
		yMin -= 1;
		yMax += 1;
	}
	const yPad = (yMax - yMin) * 0.1;
	yMin = Math.max(0, yMin - yPad);
	yMax += yPad;

	const xFor = (i: number): number =>
		opts.points.length === 1 ? padding.left + plotW / 2 : padding.left + (plotW * i) / (opts.points.length - 1);
	const yFor = (v: number): number => padding.top + plotH - ((v - yMin) / (yMax - yMin)) * plotH;

	const svg = document.createElementNS(SVG_NS, "svg");
	svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
	svg.setAttribute("class", "tmp-chart-svg");

	// Horizontal gridlines + y-axis euro labels
	const gridSteps = 4;
	for (let i = 0; i <= gridSteps; i++) {
		const v = yMin + ((yMax - yMin) * i) / gridSteps;
		const y = yFor(v);
		const line = document.createElementNS(SVG_NS, "line");
		line.setAttribute("x1", String(padding.left));
		line.setAttribute("x2", String(width - padding.right));
		line.setAttribute("y1", String(y));
		line.setAttribute("y2", String(y));
		line.setAttribute("class", "tmp-chart-grid");
		svg.appendChild(line);

		const label = document.createElementNS(SVG_NS, "text");
		label.setAttribute("x", String(padding.left - 8));
		label.setAttribute("y", String(y + 4));
		label.setAttribute("text-anchor", "end");
		label.setAttribute("class", "tmp-chart-axis-label");
		label.textContent = formatEuro(v, currency);
		svg.appendChild(label);
	}

	// X-axis month labels (only at month boundaries to avoid clutter)
	let lastMonth = "";
	opts.points.forEach((p, i) => {
		const month = p.date.slice(0, 7);
		if (month === lastMonth) return;
		lastMonth = month;
		const label = document.createElementNS(SVG_NS, "text");
		label.setAttribute("x", String(xFor(i)));
		label.setAttribute("y", String(height - 8));
		label.setAttribute("text-anchor", "middle");
		label.setAttribute("class", "tmp-chart-axis-label");
		label.textContent = formatMonth(p.date);
		svg.appendChild(label);
	});

	// Annotation line (e.g. "lowest price in 6 months")
	if (opts.annotation) {
		const y = yFor(opts.annotation.value);
		const line = document.createElementNS(SVG_NS, "line");
		line.setAttribute("x1", String(padding.left));
		line.setAttribute("x2", String(width - padding.right));
		line.setAttribute("y1", String(y));
		line.setAttribute("y2", String(y));
		line.setAttribute("class", "tmp-chart-annotation");
		svg.appendChild(line);

		const label = document.createElementNS(SVG_NS, "text");
		label.setAttribute("x", String(width - padding.right));
		label.setAttribute("y", String(y - 6));
		label.setAttribute("text-anchor", "end");
		label.setAttribute("class", "tmp-chart-annotation-label");
		label.textContent = opts.annotation.label;
		svg.appendChild(label);
	}

	svg.appendChild(buildPath(opts.points, (p) => p.min, xFor, yFor, "tmp-chart-line-min", false));
	svg.appendChild(buildPath(opts.points, (p) => p.avg, xFor, yFor, "tmp-chart-line-avg", true));

	container.appendChild(svg);
}

function buildPath(
	points: PriceHistoryPoint[],
	pick: (p: PriceHistoryPoint) => number,
	xFor: (i: number) => number,
	yFor: (v: number) => number,
	cls: string,
	dashed: boolean
): SVGPathElement {
	const d = points.map((p, i) => `${i === 0 ? "M" : "L"} ${xFor(i)} ${yFor(pick(p))}`).join(" ");
	const path = document.createElementNS(SVG_NS, "path");
	path.setAttribute("d", d);
	path.setAttribute("fill", "none");
	if (dashed) path.setAttribute("stroke-dasharray", "5,4");
	path.setAttribute("class", cls);
	return path;
}

function formatEuro(value: number, currency: string): string {
	try {
		return new Intl.NumberFormat("nl-NL", {
			style: "currency",
			currency,
			maximumFractionDigits: 0,
		}).format(value);
	} catch {
		return `€${Math.round(value)}`;
	}
}

function formatMonth(iso: string): string {
	const d = new Date(iso);
	if (Number.isNaN(d.getTime())) return iso;
	return d.toLocaleDateString("en-US", { month: "short" });
}
