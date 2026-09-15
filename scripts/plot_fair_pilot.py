#!/usr/bin/env python3
import csv
from html import escape
from pathlib import Path


root = Path(__file__).resolve().parents[1]
input_path = root / "fair_study" / "results" / "fair_pilot_metrics.csv"
output_path = root / "fair_study" / "results" / "fair_pilot_comparison.svg"

with input_path.open(newline="") as handle:
    rows = list(csv.DictReader(handle))

order = [
    ("vector", "1"),
    ("vector", "10"),
    ("scalar", "1"),
    ("scalar", "6.31"),
]
labels = ["Vector 1", "Vector 10", "Scalar 1", "Scalar 6.31"]
feature_sets = ["electron", "electron_qa2"]
colors = {"electron": "#2ca02c", "electron_qa2": "#9467bd"}
lookup = {
    (row["signal_type"], f'{float(row["mass_GeV"]):g}', row["feature_set"]): row
    for row in rows
}

width, height = 1000, 600
left, right, top, bottom = 90, 30, 70, 105
plot_width = width - left - right
plot_height = height - top - bottom
y_min, y_max = 0.96, 1.32


def y_position(value):
    return top + (y_max - value) * plot_height / (y_max - y_min)


def text(x, y, value, size=14, anchor="middle", weight="normal", rotate=None):
    transform = f' transform="rotate({rotate} {x} {y})"' if rotate else ""
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-family="Arial, sans-serif" '
        f'font-size="{size}" font-weight="{weight}" text-anchor="{anchor}"'
        f'{transform}>{escape(value)}</text>'
    )


svg = [
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
    '<rect width="100%" height="100%" fill="white"/>',
    '<defs>',
    '<pattern id="greenHatch" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">',
    '<rect width="8" height="8" fill="#2ca02c"/><line x1="0" y1="0" x2="0" y2="8" stroke="white" stroke-width="2"/></pattern>',
    '<pattern id="purpleHatch" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">',
    '<rect width="8" height="8" fill="#9467bd"/><line x1="0" y1="0" x2="0" y2="8" stroke="white" stroke-width="2"/></pattern>',
    '</defs>',
    text(width / 2, 30, "Fair parton-level comparison on held-out weighted events", 20, weight="bold"),
    text(width / 2, 53, "Common starting point: published Table I preselection", 13),
]

for tick in [0.96, 1.00, 1.08, 1.16, 1.24, 1.32]:
    y = y_position(tick)
    svg.append(f'<line x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}" stroke="#d9d9d9" stroke-width="1"/>')
    svg.append(text(left - 10, y + 5, f"{tick:.2f}", 12, anchor="end"))

baseline_y = y_position(1.0)
svg.append(f'<line x1="{left}" y1="{baseline_y:.1f}" x2="{width-right}" y2="{baseline_y:.1f}" stroke="black" stroke-width="1.5" stroke-dasharray="7,5"/>')

group_width = plot_width / len(order)
bar_width = 36
offsets = [-1.65, -0.55, 0.55, 1.65]
series = [
    ("electron", "optimized_cut", "url(#greenHatch)"),
    ("electron", "ml", colors["electron"]),
    ("electron_qa2", "optimized_cut", "url(#purpleHatch)"),
    ("electron_qa2", "ml", colors["electron_qa2"]),
]

for group_index, ((signal_type, mass), label) in enumerate(zip(order, labels)):
    center = left + group_width * (group_index + 0.5)
    for series_index, (feature_set, method, fill) in enumerate(series):
        row = lookup[(signal_type, mass, feature_set)]
        value = float(row[f"{method}_RZ_vs_paper_preselection"])
        x = center + offsets[series_index] * bar_width - bar_width / 2
        y = y_position(max(value, y_min))
        base = y_position(y_min)
        svg.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width}" height="{base-y:.1f}" '
            f'fill="{fill}" stroke="black" stroke-width="0.8"/>'
        )
        svg.append(text(x + bar_width / 2, y - 6, f"{value:.3f}", 10))
    svg.append(text(center, height - bottom + 28, label, 13))

svg.extend([
    f'<line x1="{left}" y1="{top}" x2="{left}" y2="{height-bottom}" stroke="black" stroke-width="1.5"/>',
    f'<line x1="{left}" y1="{height-bottom}" x2="{width-right}" y2="{height-bottom}" stroke="black" stroke-width="1.5"/>',
    text(24, top + plot_height / 2, "R_Z relative to Table I preselection", 14, rotate=-90),
    text(width / 2, height - 35, "Signal and mass [GeV]", 14),
])

legend = [
    ("url(#greenHatch)", "electron only: optimized cuts"),
    (colors["electron"], "electron only: BDT"),
    ("url(#purpleHatch)", "electron + truth Q_A^2: optimized cuts"),
    (colors["electron_qa2"], "electron + truth Q_A^2: BDT"),
]
legend_y = height - 73
legend_start = 118
legend_step = 218
for index, (fill, label) in enumerate(legend):
    x = legend_start + index * legend_step
    svg.append(f'<rect x="{x}" y="{legend_y}" width="22" height="14" fill="{fill}" stroke="black" stroke-width="0.7"/>')
    svg.append(text(x + 29, legend_y + 12, label, 11, anchor="start"))

svg.append('</svg>')
output_path.write_text("\n".join(svg) + "\n", encoding="utf-8")
print(f"wrote {output_path}")
