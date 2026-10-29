#!/usr/bin/env python3
"""Plot published and our calculated vector/scalar cross sections."""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D


SCRIPT_DIR = Path(__file__).resolve().parent

# Support both the audit workspace and the final Dark project layout.
if SCRIPT_DIR.name == "scripts":
    PROJECT = SCRIPT_DIR.parent
    PAPER = PROJECT / "config" / "paper_figure2_digitized.csv"
    VECTOR = PROJECT / "results" / "vector_scan_fresh.csv"
    SCALAR = PROJECT / "results" / "scalar_scan.csv"
    OUTPUT = PROJECT / "plots" / "vector_scalar_cross_section_validation"
else:
    PAPER = Path("/Users/rojaemighty/Dark/config/paper_figure2_digitized.csv")
    VECTOR = SCRIPT_DIR / "vector_scan_fresh.csv"
    SCALAR = SCRIPT_DIR / "scalar_scan.csv"
    OUTPUT = SCRIPT_DIR / "vector_scalar_cross_section_validation"


def read_csv(path: Path) -> list[dict[str, float | None]]:
    with path.open(newline="") as stream:
        rows = []
        for row in csv.DictReader(stream):
            rows.append(
                {
                    key: float(value) if value not in (None, "") else None
                    for key, value in row.items()
                }
            )
        return rows


def column(rows: list[dict[str, float | None]], name: str) -> list[float]:
    return [float(row[name]) for row in rows if row[name] is not None]


def paired(
    rows: list[dict[str, float | None]], value: str
) -> tuple[list[float], list[float]]:
    selected = [row for row in rows if row[value] is not None]
    return (
        [float(row["mass_GeV"]) for row in selected],
        [float(row[value]) for row in selected],
    )


def main() -> None:
    paper = read_csv(PAPER)
    vector = read_csv(VECTOR)
    scalar = read_csv(SCALAR)

    fig, ax = plt.subplots(figsize=(10.5, 7.2), constrained_layout=True)

    for value, color, linestyle in (
        ("vector_total_pb", "#171717", "-"),
        ("scalar_total_pb", "#171717", "--"),
        ("vector_after_cuts_pb", "#d62728", "-"),
        ("scalar_after_cuts_pb", "#d62728", "--"),
    ):
        x, y = paired(paper, value)
        ax.plot(x, y, color=color, linestyle=linestyle, linewidth=2.5, zorder=2)

    # Our results are connected lines: solid for vectors and dashed
    # for scalars, matching the line-style convention of the published curves.
    for rows, value, color, linestyle in (
        (vector, "sigma_total_pb", "#2e8b57", "-"),
        (scalar, "sigma_total_pb", "#2e8b57", "--"),
        (vector, "sigma_paper_cut_pb", "#7b3294", "-"),
        (scalar, "sigma_paper_cut_pb", "#7b3294", "--"),
    ):
        x, y = paired(rows, value)
        ax.plot(x, y, color=color, linestyle=linestyle, linewidth=2.3, zorder=3)

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(0.008, 12.0)
    ax.set_ylim(5e-4, 3.5e5)
    ax.set_xlabel(r"$m_\phi$ [GeV]", fontsize=14)
    ax.set_ylabel(r"$\sigma(e\mathrm{Au}\to e\mathrm{Au}\phi)$ [pb]", fontsize=14)
    ax.set_title(
        r"Vector and scalar comparison, $g^{e}_{V(S)}=10^{-4}$",
        fontsize=15,
        pad=12,
    )
    ax.grid(which="major", color="#9a9a9a", alpha=0.25, linewidth=0.8)
    ax.grid(which="minor", color="#bdbdbd", alpha=0.12, linewidth=0.5)
    ax.tick_params(axis="both", which="both", labelsize=11, direction="in")
    ax.text(
        0.985,
        0.975,
        r"Our implementation; authors' corrected cut normalization agrees",
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=9.0,
        color="#555555",
    )

    dataset_handles = [
        Line2D([0], [0], color="#171717", lw=2.5, label="Published, inclusive"),
        Line2D([0], [0], color="#d62728", lw=2.5, label="Published cuts (superseded normalization)"),
        Line2D([0], [0], color="#2e8b57", lw=2.3, label="Our implementation, inclusive"),
        Line2D([0], [0], color="#7b3294", lw=2.3, label="Our implementation, Table I cuts"),
    ]
    style_handles = [
        Line2D([0], [0], color="#555555", lw=2.5, ls="-", label="Vector boson"),
        Line2D([0], [0], color="#555555", lw=2.5, ls="--", label="Scalar boson"),
    ]
    dataset_legend = ax.legend(
        handles=dataset_handles,
        title="Calculation and selection",
        loc="lower left",
        bbox_to_anchor=(0.015, 0.02),
        frameon=True,
        framealpha=0.93,
        fontsize=9.5,
        title_fontsize=10.5,
    )
    ax.add_artist(dataset_legend)
    ax.legend(
        handles=style_handles,
        title="Boson type",
        loc="lower left",
        bbox_to_anchor=(0.39, 0.02),
        frameon=True,
        framealpha=0.93,
        fontsize=9.5,
        title_fontsize=10.5,
    )

    fig.savefig(OUTPUT.with_suffix(".pdf"))
    fig.savefig(OUTPUT.with_suffix(".png"), dpi=240)
    print(f"wrote {OUTPUT.with_suffix('.pdf')} and {OUTPUT.with_suffix('.png')}")


if __name__ == "__main__":
    main()
