#!/usr/bin/env python3
"""Plot BDT-versus-cuts mass scans and independent-run results."""

from __future__ import annotations

import csv
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
FULL = ROOT / "fair_study" / "rigorous" / "final" / "rigorous_final_metrics.csv"
SEEDS = ROOT / "fair_study" / "seed_robustness" / "run_20260814T063518Z" / "benchmark_summary.csv"
T_SEEDS = ROOT / "fair_study" / "t_seed_robustness" / "run_t_20260820_final" / "benchmark_summary.csv"
OUT_VECTOR = ROOT / "plots" / "ml_fair_vector_t_comparison.png"
OUT_SCALAR = ROOT / "plots" / "ml_fair_scalar_t_comparison.png"
OUT_SEEDS = ROOT / "plots" / "ml_seed_robustness.png"
OUT_T_SEEDS = ROOT / "plots" / "ml_t_seed_robustness.png"

GREEN = "#2E8B57"
PURPLE = "#7651A8"
BLACK = "#202020"
BLUE = "#2563EB"
INK = "#20242A"
MUTED = "#58616D"
GRID = "#D9DEE5"
WHITE = "#FFFFFF"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf"),
        Path("/System/Library/Fonts/Supplemental/Helvetica.ttc"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


F_TITLE = font(43, True)
F_PANEL = font(35, True)
F_AXIS = font(29)
F_TICK = font(25)
F_LEGEND = font(25)
F_NOTE = font(23)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def centered(draw: ImageDraw.ImageDraw, xy: tuple[float, float], text: str, fnt, fill=INK) -> None:
    box = draw.textbbox((0, 0), text, font=fnt)
    draw.text((xy[0] - (box[2] - box[0]) / 2, xy[1] - (box[3] - box[1]) / 2), text, font=fnt, fill=fill)


def rotated_label(image: Image.Image, text: str, x: int, y: int) -> None:
    box = ImageDraw.Draw(image).textbbox((0, 0), text, font=F_AXIS)
    layer = Image.new("RGBA", (box[2] - box[0] + 20, box[3] - box[1] + 20), (255, 255, 255, 0))
    ImageDraw.Draw(layer).text((10, 10), text, font=F_AXIS, fill=INK)
    layer = layer.rotate(90, expand=True)
    image.alpha_composite(layer, (x - layer.width // 2, y - layer.height // 2))


def plot_signal_comparison(signal_type: str, output: Path) -> None:
    rows = read_csv(FULL)
    image = Image.new("RGBA", (2200, 1100), WHITE)
    draw = ImageDraw.Draw(image)
    centered(draw, (1100, 52), f"{signal_type.capitalize()} signal: effect of adding exact t", F_TITLE)

    left, top, right, bottom = 190, 145, 2070, 900
    x_min, x_max = math.log10(0.008), math.log10(12.0)
    y_min, y_max = -0.5, 1.75
    width, height = right - left, bottom - top
    map_x = lambda value: left + (math.log10(value) - x_min) / (x_max - x_min) * width
    map_y = lambda value: bottom - (value - y_min) / (y_max - y_min) * height

    for value in (-0.5, 0.0, 0.5, 1.0, 1.5):
        yy = map_y(value)
        draw.line((left, yy, right, yy), fill=GRID, width=2)
        draw.text((left - 72, yy - 14), f"{value:g}", font=F_TICK, fill=MUTED)
    for value in (0.01, 0.1, 1.0, 10.0):
        xx = map_x(value)
        draw.line((xx, top, xx, bottom), fill=GRID, width=2)
        centered(draw, (xx, bottom + 37), f"{value:g}", F_TICK, MUTED)
    draw.rectangle((left, top, right, bottom), outline=INK, width=3)
    draw.line((left, map_y(0.0), right, map_y(0.0)), fill=INK, width=3)
    y_one = map_y(1.0)
    for xx in range(left, right, 22):
        draw.line((xx, y_one, min(xx + 10, right), y_one), fill="#777777", width=3)

    series = (
        ("electron", BLACK, "Observables"),
        ("electron_qa2", BLUE, "Observables + t"),
    )
    for feature_set, color, label in series:
        subset = sorted(
            (row for row in rows if row["signal_type"] == signal_type and row["feature_set"] == feature_set),
            key=lambda row: float(row["mass_GeV"]),
        )
        points = []
        for row in subset:
            mass = float(row["mass_GeV"])
            value = 100.0 * float(row["coupling_advantage"])
            low = 100.0 * float(row["coupling_q025"])
            high = 100.0 * float(row["coupling_q975"])
            points.append((map_x(mass), map_y(value), map_y(low), map_y(high)))
        for index in range(len(points) - 1):
            draw.line((*points[index][:2], *points[index + 1][:2]), fill=color, width=5)
        for xx, yy, y_low, y_high in points:
            draw.line((xx, y_high, xx, y_low), fill=color, width=3)
            draw.line((xx - 7, y_high, xx + 7, y_high), fill=color, width=3)
            draw.line((xx - 7, y_low, xx + 7, y_low), fill=color, width=3)
            draw.ellipse((xx - 9, yy - 9, xx + 9, yy + 9), fill=color, outline=color, width=2)

    legend_y = top + 27
    for _, color, label in series:
        draw.line((left + 28, legend_y, left + 100, legend_y), fill=color, width=5)
        draw.ellipse((left + 55, legend_y - 8, left + 71, legend_y + 8), fill=color)
        draw.text((left + 120, legend_y - 15), label, font=F_LEGEND, fill=INK)
        legend_y += 45

    centered(draw, ((left + right) / 2, bottom + 82), "Boson mass m_phi [GeV]", F_AXIS)
    rotated_label(image, "BDT coupling-threshold advantage over cuts [%]", 52, 530)
    centered(draw, (1100, 1048), "Both the BDT and optimized cuts receive the same inputs in each curve", F_NOTE, MUTED)
    output.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(output, quality=95)


def plot_seed_study() -> None:
    rows = read_csv(SEEDS)
    order = [("vector", 1.0), ("vector", 10.0), ("scalar", 1.0), ("scalar", 6.31)]
    lookup = {(row["signal_type"], float(row["mass_GeV"])): row for row in rows}
    labels = ["Vector, 1 GeV", "Vector, 10 GeV", "Scalar, 1 GeV", "Scalar, 6.31 GeV"]
    colors = [BLACK, BLACK, BLACK, BLACK]
    values = [100.0 * float(lookup[key]["hierarchical_coupling_q50"]) for key in order]
    lower = [100.0 * float(lookup[key]["hierarchical_coupling_q025"]) for key in order]
    upper = [100.0 * float(lookup[key]["hierarchical_coupling_q975"]) for key in order]

    image = Image.new("RGB", (2200, 1040), WHITE)
    draw = ImageDraw.Draw(image)
    centered(draw, (1100, 55), "Ten independent event generation and training runs", F_TITLE)
    centered(draw, (1100, 105), "Hierarchical medians and 95% intervals; all lie inside the preregistered +/-1% equivalence margin", F_NOTE, MUTED)
    left, right, top, bottom = 520, 2060, 180, 850
    x_min, x_max = -0.22, 0.22
    map_x = lambda value: left + (value - x_min) / (x_max - x_min) * (right - left)
    y_positions = [255, 420, 585, 750]

    for tick in (-0.2, -0.1, 0.0, 0.1, 0.2):
        xx = map_x(tick)
        draw.line((xx, top, xx, bottom), fill=GRID, width=2)
        centered(draw, (xx, bottom + 42), f"{tick:+.1f}", F_TICK, MUTED)
    draw.line((map_x(0.0), top, map_x(0.0), bottom), fill=INK, width=4)

    for y, label, color, value, low, high in zip(y_positions, labels, colors, values, lower, upper):
        draw.text((40, y - 18), label, font=F_PANEL, fill=INK)
        x_low, x_mid, x_high = map_x(low), map_x(value), map_x(high)
        draw.line((x_low, y, x_high, y), fill=color, width=6)
        draw.line((x_low, y - 13, x_low, y + 13), fill=color, width=4)
        draw.line((x_high, y - 13, x_high, y + 13), fill=color, width=4)
        draw.ellipse((x_mid - 11, y - 11, x_mid + 11, y + 11), fill=color, outline=color)
        text = f"{value:+.3f}%  [{low:+.3f}, {high:+.3f}]"
        box = draw.textbbox((0, 0), text, font=F_TICK)
        draw.text((right - (box[2] - box[0]), y - 52), text, font=F_TICK, fill=MUTED)

    centered(draw, ((left + right) / 2, 945), "BDT coupling-threshold advantage over cuts [%]", F_AXIS)
    OUT_SEEDS.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUT_SEEDS, quality=95)


def plot_t_seed_study() -> None:
    rows = read_csv(T_SEEDS)
    order = [("vector", 10.0), ("scalar", 10.0)]
    lookup = {(row["signal_type"], float(row["mass_GeV"])): row for row in rows}
    labels = ["Vector, 10 GeV", "Scalar, 10 GeV"]
    values = [100.0 * float(lookup[key]["hierarchical_coupling_q50"]) for key in order]
    lower = [100.0 * float(lookup[key]["hierarchical_coupling_q025"]) for key in order]
    upper = [100.0 * float(lookup[key]["hierarchical_coupling_q975"]) for key in order]

    image = Image.new("RGB", (2200, 940), WHITE)
    draw = ImageDraw.Draw(image)
    centered(draw, (1100, 55), "Observables + exact t: ten independent runs", F_TITLE)
    centered(draw, (1100, 105), "Both methods use identical inputs; median estimates and 95% intervals", F_NOTE, MUTED)
    left, right, top, bottom = 520, 2060, 180, 735
    x_min, x_max = 0.75, 1.65
    map_x = lambda value: left + (value - x_min) / (x_max - x_min) * (right - left)
    y_positions = [310, 590]

    for tick in (0.8, 1.0, 1.2, 1.4, 1.6):
        xx = map_x(tick)
        draw.line((xx, top, xx, bottom), fill=GRID, width=2)
        centered(draw, (xx, bottom + 42), f"{tick:.1f}", F_TICK, MUTED)
    for value, color, width in ((1.0, "#777777", 3),):
        xx = map_x(value)
        for yy in range(top, bottom, 22):
            draw.line((xx, yy, xx, min(yy + 10, bottom)), fill=color, width=width)

    for y, label, value, low, high in zip(y_positions, labels, values, lower, upper):
        draw.text((40, y - 18), label, font=F_PANEL, fill=INK)
        x_low, x_mid, x_high = map_x(low), map_x(value), map_x(high)
        draw.line((x_low, y, x_high, y), fill=BLUE, width=6)
        draw.line((x_low, y - 13, x_low, y + 13), fill=BLUE, width=4)
        draw.line((x_high, y - 13, x_high, y + 13), fill=BLUE, width=4)
        draw.ellipse((x_mid - 12, y - 12, x_mid + 12, y + 12), fill=BLUE, outline=BLUE)
        text = f"{value:+.3f}%  [{low:+.3f}, {high:+.3f}]"
        box = draw.textbbox((0, 0), text, font=F_TICK)
        draw.text((right - (box[2] - box[0]), y - 57), text, font=F_TICK, fill=MUTED)

    centered(draw, ((left + right) / 2, 845), "BDT coupling-threshold advantage over cuts [%]", F_AXIS)
    OUT_T_SEEDS.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUT_T_SEEDS, quality=95)


if __name__ == "__main__":
    plot_signal_comparison("vector", OUT_VECTOR)
    plot_signal_comparison("scalar", OUT_SCALAR)
    plot_seed_study()
    plot_t_seed_study()
    print(OUT_VECTOR)
    print(OUT_SCALAR)
    print(OUT_SEEDS)
    print(OUT_T_SEEDS)
