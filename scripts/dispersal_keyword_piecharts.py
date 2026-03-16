#!/usr/bin/env python3
"""
Draw one image with a pie chart per subfolder for the *language* of dispersal keywords.

Given a folder of subfolders (each containing parse-treatment JSON files),
collects dispersal.keywords_found per subfolder, maps each keyword to its
language (from dispersal_terms.csv and fruit_type_terms.csv), and draws a
grid of pie charts on a single image. Each pie shows the frequency of
keyword languages (e.g. French, German, Latin).

Requires: matplotlib (e.g. pip install -r requirements-plot.txt)

Usage:
  python scripts/dispersal_keyword_piecharts.py <parent_folder> [--output image.png]
  python scripts/dispersal_keyword_piecharts.py random_samples_test_lang/test_small_result -o dispersal_pies.png
"""

import argparse
import csv
import json
from pathlib import Path
from collections import Counter

import matplotlib.pyplot as plt
from matplotlib.patches import Patch

# Paths relative to repo root
REPO_ROOT = Path(__file__).resolve().parent.parent
DISPERSAL_TERMS_CSV = REPO_ROOT / "flora/pylib/rules/terms/dispersal_terms/dispersal_terms.csv"
FRUIT_TYPE_TERMS_CSV = REPO_ROOT / "flora/pylib/rules/terms/dispersal_terms/fruit_type_terms.csv"

# Colors for language slices (fixed order: french, german, english, latin, unknown, etc.)
DEFAULT_COLORS = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
    "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
]

# Full display names for legend (lowercase key -> Title Case label)
LANG_DISPLAY_NAMES: dict[str, str] = {
    "english": "English",
    "french": "French",
    "german": "German",
    "latin": "Latin",
    "portuguese": "Portuguese",
    "spanish": "Spanish",
    "turkish": "Turkish",
    "unknown": "Unknown",
}

# Subfolder name (e.g. de, en) -> full language name for pie chart titles
FOLDER_NAME_TO_LANG: dict[str, str] = {
    "de": "German",
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "la": "Latin",
    "pt": "Portuguese",
    "tr": "Turkish",
}


def lang_display_name(lang: str) -> str:
    """Return full language name for legend (e.g. 'french' -> 'French')."""
    return LANG_DISPLAY_NAMES.get(lang.lower(), lang.capitalize())


def folder_display_name(folder_name: str) -> str:
    """Return full language name for pie title (e.g. 'de' -> 'German')."""
    return FOLDER_NAME_TO_LANG.get(folder_name.lower(), folder_name.upper())


def load_keyword_to_language(dispersal_csv: Path, fruit_type_csv: Path) -> dict[str, str]:
    """Build mapping from keyword (pattern) to language from both CSVs.
    First occurrence wins: if a pattern appears in multiple languages, we keep the language
    from the first row where it was seen."""
    keyword_lang: dict[str, str] = {}
    for csv_path in (fruit_type_csv, dispersal_csv):
        if not csv_path.exists():
            continue
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                pattern = (row.get("pattern") or "").strip()
                lang = (row.get("language") or "").strip()
                if pattern and lang:
                    key = pattern.lower()
                    if key not in keyword_lang:
                        keyword_lang[key] = lang
    return keyword_lang


def collect_language_counts(folder: Path, keyword_lang: dict[str, str]) -> Counter[str]:
    """Read all JSON in folder; return Counter of keyword *language* (from keywords_found)."""
    lang_counts: Counter[str] = Counter()
    for path in folder.glob("*.json"):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        dispersal = data.get("dispersal") or {}
        keywords = dispersal.get("keywords_found")
        if not isinstance(keywords, list):
            continue
        for kw in keywords:
            if isinstance(kw, str) and kw.strip():
                lang = keyword_lang.get(kw.strip().lower(), "unknown")
                lang_counts[lang] += 1
    return lang_counts


def get_subfolders_with_jsons(parent: Path) -> list[Path]:
    """Return subfolders of parent that contain at least one .json file."""
    out = []
    for p in sorted(parent.iterdir()):
        if p.is_dir() and any(p.glob("*.json")):
            out.append(p)
    return out


def make_pie_data(lang_counts: Counter[str]) -> tuple[list[str], list[int], list[str]]:
    """Convert language counts to (labels, sizes, labels_with_count) for pie chart."""
    if not lang_counts:
        return ["(no data)"], [1], ["(no data)"]
    # Sort by count descending for consistent order
    sorted_items = lang_counts.most_common()
    labels = [k for k, _ in sorted_items]
    sizes = [c for _, c in sorted_items]
    labels_with_count = [f"{k} ({c})" for k, c in sorted_items]
    return labels, sizes, labels_with_count


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Pie charts of keyword *language* frequency per subfolder (one image).",
    )
    parser.add_argument(
        "folder",
        type=Path,
        help="Parent folder whose subfolders contain JSON files (parse-treatment output).",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output image path (default: <folder>/dispersal_keyword_piecharts.png).",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=150,
        help="Output image DPI (default: 150).",
    )
    parser.add_argument(
        "--fig-width",
        type=float,
        default=6.0,
        help="Width of each pie subplot in inches (default: 6).",
    )
    parser.add_argument(
        "--fig-height",
        type=float,
        default=5.0,
        help="Height of each pie subplot in inches (default: 5).",
    )
    args = parser.parse_args()

    parent = args.folder
    if not parent.is_absolute():
        parent = (Path.cwd() / parent).resolve()
    if not parent.is_dir():
        raise SystemExit(f"Not a directory: {parent}")

    subfolders = get_subfolders_with_jsons(parent)
    if not subfolders:
        raise SystemExit(f"No subfolders with JSON files found under {parent}")

    keyword_lang = load_keyword_to_language(DISPERSAL_TERMS_CSV, FRUIT_TYPE_TERMS_CSV)

    # Collect *language* counts per subfolder
    subfolder_name_to_lang_counts: dict[str, Counter[str]] = {}
    for sub in subfolders:
        subfolder_name_to_lang_counts[sub.name] = collect_language_counts(sub, keyword_lang)

    # One fixed color per language across all pies (sorted for consistent order)
    all_languages = sorted(
        set().union(*(set(c.keys()) for c in subfolder_name_to_lang_counts.values()))
    )
    lang_to_color = {
        lang: DEFAULT_COLORS[i % len(DEFAULT_COLORS)]
        for i, lang in enumerate(all_languages)
    }

    # Grid layout
    n = len(subfolders)
    ncols = min(n, 3)
    nrows = (n + ncols - 1) // ncols

    fig, axes = plt.subplots(
        nrows, ncols,
        figsize=(args.fig_width * ncols, args.fig_height * nrows),
        squeeze=False,
    )
    ax_flat = axes.flat

    for idx, (sub_name, lang_counts) in enumerate(subfolder_name_to_lang_counts.items()):
        ax = ax_flat[idx]
        labels, sizes, labels_with_count = make_pie_data(lang_counts)
        if not lang_counts or (len(sizes) == 1 and labels[0] == "(no data)"):
            ax.text(0.5, 0.5, "No keywords", ha="center", va="center", transform=ax.transAxes, fontsize=12)
            ax.set_title(folder_display_name(sub_name), fontsize=14)
            ax.set_aspect("equal")
            continue
        # Same color for each language in every pie (no percentage labels on slices)
        colors = [lang_to_color[lang] for lang in labels]
        ax.pie(
            sizes, labels=None, colors=colors, startangle=90, counterclock=False,
        )
        ax.set_title(folder_display_name(sub_name), fontsize=14)
        ax.set_aspect("equal")

    for idx in range(n, len(ax_flat)):
        ax_flat[idx].set_visible(False)

    # Single shared legend for all languages (full language names)
    legend_handles = [
        Patch(facecolor=lang_to_color[lang], label=lang_display_name(lang), edgecolor="gray", linewidth=0.5)
        for lang in all_languages
    ]
    fig.legend(
        handles=legend_handles,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.02),
        ncol=min(len(all_languages), 5),
        fontsize=12,
        frameon=True,
    )

    plt.tight_layout(rect=[0, 0.08, 1, 1])  # leave space for bottom legend

    out = args.output
    if out is None:
        out = parent / "dispersal_keyword_piecharts.png"
    elif not out.is_absolute():
        out = Path.cwd() / out
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=args.dpi, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out}")


if __name__ == "__main__":
    main()
