#!/usr/bin/env python3
"""
Plot dispersal trait extraction stats from FloraTraiter JSON output.

Given a directory of JSON files, reads each file's "dispersal"."traits" and produces:
- Per binary trait: bar plot of presence vs absence vs unknown (counts or %).
- Fruit type: bar of "fruit type extracted" vs "no fruit type"; and a chart of specific fruit types (bar or pie).

Usage:
  python plot_dispersal_traits.py --json-dir random_samples/test_medium_result/english [--out-dir plots]

Requires: matplotlib, numpy (pip install matplotlib numpy)
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    import matplotlib.pyplot as plt
    import numpy as np
except ImportError as e:
    raise SystemExit("Missing dependency. Install with: pip install matplotlib numpy") from e

# Binary dispersal traits (same as flora.pylib.const.DISPERSAL_TRAIT_NAMES)
BINARY_TRAIT_NAMES = [
    "wing",
    "pappus_plume_coma",
    "fleshy_reward",
    "hooks_barbs_spines_burrs",
    "sticky_coating",
    "elaiosome_carruncle",
    "buoyant_structure",
    "ballistic_structure",
    "protective_tissue",
]

FRUIT_TYPE_KEY = "fruitType"


def load_traits_from_jsons(json_dir: Path) -> list[dict]:
    """Load dispersal.traits from every JSON in json_dir. Returns list of trait dicts."""
    trait_list = []
    json_dir = Path(json_dir)
    if not json_dir.is_dir():
        raise NotADirectoryError(str(json_dir))
    for path in sorted(json_dir.glob("*.json")):
        try:
            with path.open(encoding="utf-8") as f:
                data = json.load(f)
            dispersal = data.get("dispersal") or {}
            traits = dispersal.get("traits")
            if traits is None:
                traits = {}
            if not isinstance(traits, dict):
                traits = {}
            trait_list.append(traits)
        except (json.JSONDecodeError, OSError) as e:
            print(f"Warning: skip {path}: {e}")
    return trait_list


def classify_binary(traits: dict) -> dict[str, str]:
    """
    For each binary trait, return 'presence' | 'absence' | 'unknown'.
    - presence: key in traits and value is truthy (e.g. 1)
    - absence: key in traits and value is falsy (e.g. 0)
    - unknown: key not in traits
    """
    out = {}
    for name in BINARY_TRAIT_NAMES:
        if name not in traits:
            out[name] = "unknown"
        elif traits[name]:
            out[name] = "presence"
        else:
            out[name] = "absence"
    return out


def aggregate_binary(trait_list: list[dict]) -> dict[str, dict[str, int]]:
    """Aggregate counts: trait_name -> { presence, absence, unknown }."""
    counts = {name: {"presence": 0, "absence": 0, "unknown": 0} for name in BINARY_TRAIT_NAMES}
    for traits in trait_list:
        for name, status in classify_binary(traits).items():
            counts[name][status] += 1
    return counts


def aggregate_fruit_type(trait_list: list[dict]) -> tuple[int, int]:
    """Return (n_with_fruit_type, n_without)."""
    with_ft = 0
    without_ft = 0
    for traits in trait_list:
        val = traits.get(FRUIT_TYPE_KEY)
        if val is not None and str(val).strip():
            with_ft += 1
        else:
            without_ft += 1
    return with_ft, without_ft


def aggregate_fruit_type_values(trait_list: list[dict]) -> dict[str, int]:
    """Return count per fruit type label (e.g. berry, capsule). Include 'No fruit type' for missing."""
    counts: dict[str, int] = {}
    for traits in trait_list:
        val = traits.get(FRUIT_TYPE_KEY)
        if val is not None and str(val).strip():
            label = str(val).strip()
            counts[label] = counts.get(label, 0) + 1
        else:
            counts["No fruit type"] = counts.get("No fruit type", 0) + 1
    return counts


def plot_binary_traits(
    counts: dict[str, dict[str, int]],
    n_total: int,
    out_path: Path,
    use_percent: bool = True,
) -> None:
    """One subplot per binary trait: presence / absence / unknown bars."""
    n_traits = len(BINARY_TRAIT_NAMES)
    n_cols = 3
    n_rows = (n_traits + n_cols - 1) // n_cols
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(4 * n_cols, 3 * n_rows))
    if n_traits == 1:
        axes = np.array([axes])
    axes = axes.flatten()

    categories = ["presence", "absence", "unknown"]
    colors = ["#2ecc71", "#e74c3c", "#95a5a6"]
    x = np.arange(len(categories))
    width = 0.6

    for i, name in enumerate(BINARY_TRAIT_NAMES):
        ax = axes[i]
        c = counts[name]
        vals = [c["presence"], c["absence"], c["unknown"]]
        if use_percent and n_total:
            vals = [100 * v / n_total for v in vals]
        bars = ax.bar(x, vals, width=width, color=colors)
        ax.set_xticks(x)
        ax.set_xticklabels(["Presence", "Absence", "Unknown"], rotation=15, ha="right")
        ax.set_ylabel("Percent" if use_percent else "Count")
        ax.set_title(name.replace("_", " "))
        if not use_percent:
            ax.set_ylabel("Count")
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, b.get_height() + (0.02 * max(vals) if vals else 0),
                   f"{v:.1f}" if use_percent else str(int(v)),
                   ha="center", va="bottom", fontsize=8)

    for j in range(i + 1, len(axes)):
        axes[j].set_visible(False)
    fig.suptitle("Binary dispersal traits: presence vs absence vs unknown", fontsize=12, y=1.02)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()


def plot_fruit_type_pct(n_with: int, n_without: int, out_path: Path) -> None:
    """Bar: fruit type extracted vs no fruit type (percentages)."""
    n_total = n_with + n_without
    if n_total == 0:
        return
    pct_with = 100 * n_with / n_total
    pct_without = 100 * n_without / n_total

    fig, ax = plt.subplots(figsize=(6, 4))
    labels = ["Fruit type extracted", "No fruit type"]
    sizes = [pct_with, pct_without]
    colors = ["#3498db", "#bdc3c7"]
    bars = ax.bar(labels, sizes, color=colors, edgecolor="gray")
    ax.set_ylabel("Percentage")
    ax.set_ylim(0, 100)
    for b, v in zip(bars, sizes):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 1, f"{v:.1f}%",
                ha="center", va="bottom", fontsize=11)
    ax.set_title("Fruit type extraction rate")
    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()


def plot_fruit_type_distribution(
    type_counts: dict[str, int],
    out_path: Path,
    use_pie: bool = False,
    min_share_pct: float = 0,
) -> None:
    """Bar chart or pie of specific fruit types. Sorts by count descending."""
    if not type_counts:
        return
    n_total = sum(type_counts.values())
    if n_total == 0:
        return
    # Sort by count descending; keep order deterministic for ties
    sorted_items = sorted(type_counts.items(), key=lambda x: (-x[1], x[0]))
    labels = [x[0] for x in sorted_items]
    counts = [x[1] for x in sorted_items]
    pcts = [100 * c / n_total for c in counts]
    if min_share_pct > 0:
        kept = [(l, c, p) for l, c, p in zip(labels, counts, pcts) if p >= min_share_pct]
        other_count = sum(c for l, c, p in zip(labels, counts, pcts) if p < min_share_pct)
        if other_count and kept:
            kept.append(("Other", other_count, 100 * other_count / n_total))
        if not kept:
            kept = list(zip(labels, counts, pcts))
        labels, counts, pcts = [x[0] for x in kept], [x[1] for x in kept], [x[2] for x in kept]

    if use_pie:
        fig, ax = plt.subplots(figsize=(8, 8))
        colors = plt.cm.Set3(np.linspace(0, 1, len(labels)))
        if "No fruit type" in labels:
            idx = labels.index("No fruit type")
            colors[idx] = (0.74, 0.76, 0.78, 1.0)
        wedges, texts, autotexts = ax.pie(
            counts, labels=labels, autopct="%1.1f%%", colors=colors, startangle=90
        )
        for t in texts:
            t.set_fontsize(9)
        ax.set_title("Fruit type distribution")
        plt.tight_layout()
    else:
        # Horizontal bar: labels on y-axis
        n_bars = len(labels)
        fig, ax = plt.subplots(figsize=(8, max(5, n_bars * 0.35)))
        y_pos = np.arange(n_bars)
        bars = ax.barh(y_pos, counts, color=plt.cm.Set3(np.linspace(0, 1, n_bars)))
        if "No fruit type" in labels:
            idx = labels.index("No fruit type")
            bars[idx].set_color("#bdc3c7")
        ax.set_yticks(y_pos)
        ax.set_yticklabels(labels, fontsize=10)
        ax.invert_yaxis()
        ax.set_xlabel("Count")
        ax.set_title("Fruit type distribution")
        for i, (c, p) in enumerate(zip(counts, pcts)):
            ax.text(c + 0.02 * max(counts), i, f"{c} ({p:.1f}%)", va="center", fontsize=9)
        plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Plot dispersal trait presence/absence and fruit type extraction from JSON dir."
    )
    parser.add_argument(
        "--json-dir",
        type=Path,
        required=True,
        help="Directory containing FloraTraiter JSON files",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Directory for output plots (default: same as json-dir)",
    )
    parser.add_argument(
        "--counts",
        action="store_true",
        help="Use raw counts instead of percentages for binary traits",
    )
    parser.add_argument(
        "--pie",
        action="store_true",
        help="Use pie chart for fruit type distribution (default: horizontal bar)",
    )
    parser.add_argument(
        "--min-share-pct",
        type=float,
        default=0,
        metavar="PCT",
        help="In pie chart, group types below this %% into 'Other' (default: 0)",
    )
    args = parser.parse_args()
    json_dir = args.json_dir
    out_dir = args.out_dir or json_dir
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    trait_list = load_traits_from_jsons(json_dir)
    n_total = len(trait_list)
    if n_total == 0:
        print("No JSON files found. Exiting.")
        return

    # Binary traits
    binary_counts = aggregate_binary(trait_list)
    plot_binary_traits(
        binary_counts,
        n_total,
        out_dir / "dispersal_binary_traits.png",
        use_percent=not args.counts,
    )
    print(f"Saved {out_dir / 'dispersal_binary_traits.png'} (n={n_total})")

    # Fruit type: extraction rate
    n_with_ft, n_without_ft = aggregate_fruit_type(trait_list)
    plot_fruit_type_pct(n_with_ft, n_without_ft, out_dir / "dispersal_fruit_type.png")
    print(f"Saved {out_dir / 'dispersal_fruit_type.png'} (fruit type: {n_with_ft}/{n_total}, no: {n_without_ft})")

    # Fruit type: specific types distribution
    type_counts = aggregate_fruit_type_values(trait_list)
    dist_path = out_dir / "dispersal_fruit_type_distribution.png"
    plot_fruit_type_distribution(
        type_counts,
        dist_path,
        use_pie=args.pie,
        min_share_pct=args.min_share_pct,
    )
    print(f"Saved {dist_path} (fruit types: {len([k for k in type_counts if k != 'No fruit type'])} unique)")


if __name__ == "__main__":
    main()
