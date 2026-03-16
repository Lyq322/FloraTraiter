#!/usr/bin/env python3
"""
Stats on dispersal keywords from parse-treatment JSON output.

Reads a folder of JSON files (parse-treatment results), collects
dispersal.keywords_found, and reports:
- Relative frequencies of keyword language (from dispersal_terms.csv and fruit_type_terms.csv)
- Top keywords overall
- Top keywords per language

Usage:
  python scripts/dispersal_keyword_stats.py <folder>
  python scripts/dispersal_keyword_stats.py random_samples_test_lang/test_small_result/de
"""

import argparse
import csv
import json
from pathlib import Path
from collections import Counter, defaultdict

# Paths relative to repo root
REPO_ROOT = Path(__file__).resolve().parent.parent
DISPERSAL_TERMS_CSV = REPO_ROOT / "flora/pylib/rules/terms/dispersal_terms/dispersal_terms.csv"
FRUIT_TYPE_TERMS_CSV = REPO_ROOT / "flora/pylib/rules/terms/dispersal_terms/fruit_type_terms.csv"


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


def collect_from_folder(
    folder: Path,
    keyword_lang: dict[str, str],
) -> tuple[Counter[str], Counter[str], defaultdict[str, Counter], dict[str, list[str]]]:
    """
    Scan folder for JSON files, read dispersal.keywords_found.
    Returns (language_counts, keyword_counts_overall, keyword_by_lang, keyword_to_files).
    keyword_to_files: keyword -> list of file stems (e.g. "wfo-0000213949_Flora_Helvetica_021505").
    """
    language_counts: Counter = Counter()
    keyword_overall: Counter = Counter()
    keyword_by_lang: dict[str, Counter] = defaultdict(Counter)
    keyword_to_files: dict[str, list[str]] = defaultdict(list)  # unique stems per kw

    for path in sorted(folder.glob("*.json")):
        stem = path.stem  # original txt name without .txt
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue

        dispersal = data.get("dispersal") or {}
        keywords = dispersal.get("keywords_found")
        if not isinstance(keywords, list):
            continue

        added_for_this_file: set[str] = set()  # kws we already added this stem for
        for kw in keywords:
            if not isinstance(kw, str):
                continue
            kw = kw.strip()
            if not kw:
                continue
            lang = keyword_lang.get(kw.lower(), "unknown")
            language_counts[lang] += 1
            keyword_overall[kw] += 1
            keyword_by_lang[lang][kw] += 1
            if kw not in added_for_this_file:
                added_for_this_file.add(kw)
                keyword_to_files[kw].append(stem)

    return language_counts, keyword_overall, keyword_by_lang, keyword_to_files


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Dispersal keyword stats from parse-treatment JSON folder."
    )
    parser.add_argument(
        "folder",
        type=Path,
        help="Folder containing JSON files (parse-treatment result)",
    )
    parser.add_argument(
        "-n",
        "--top-n",
        type=int,
        default=20,
        help="Number of top keywords to show (default: 20)",
    )
    parser.add_argument(
        "-e",
        "--examples",
        type=int,
        default=3,
        metavar="N",
        help="Number of example .txt file names to show per keyword (default: 3). Use 0 or --no-examples to omit.",
    )
    parser.add_argument(
        "--no-examples",
        action="store_true",
        help="Do not print example file names for each keyword.",
    )
    args = parser.parse_args()
    if args.no_examples:
        args.examples = 0

    folder = args.folder
    if not folder.is_absolute():
        folder = (Path.cwd() / folder).resolve()
    if not folder.is_dir():
        raise SystemExit(f"Not a directory: {folder}")

    keyword_lang = load_keyword_to_language(DISPERSAL_TERMS_CSV, FRUIT_TYPE_TERMS_CSV)
    language_counts, keyword_overall, keyword_by_lang, keyword_to_files = collect_from_folder(
        folder, keyword_lang
    )

    total = sum(language_counts.values())
    if total == 0:
        print("No dispersal keywords found in any JSON in the folder.")
        return

    # ---- Relative frequencies of language ----
    print("=" * 60)
    print("Language (relative frequency)")
    print("=" * 60)
    for lang, count in language_counts.most_common():
        pct = 100.0 * count / total
        print(f"  {lang}: {count} ({pct:.1f}%)")
    print()

    def example_files(kw: str, max_examples: int) -> str:
        files = keyword_to_files.get(kw, [])
        if not files or max_examples <= 0:
            return ""
        names = [f"{s}.txt" for s in files[:max_examples]]
        return "  e.g. " + ", ".join(names)

    # ---- Top keywords overall ----
    print("=" * 60)
    print(f"Top {args.top_n} keywords overall")
    print("=" * 60)
    for kw, count in keyword_overall.most_common(args.top_n):
        lang = keyword_lang.get(kw.lower(), "unknown")
        print(f"  {count:5d}  {kw}  [{lang}]")
        ex = example_files(kw, args.examples)
        if ex:
            print(ex)
    print()

    # ---- Top keywords per language ----
    print("=" * 60)
    print(f"Top {args.top_n} keywords per language")
    print("=" * 60)
    for lang in sorted(keyword_by_lang.keys(), key=lambda l: (-language_counts[l], l)):
        c = keyword_by_lang[lang]
        print(f"\n  --- {lang} ---")
        for kw, count in c.most_common(args.top_n):
            print(f"  {count:5d}  {kw}")
            ex = example_files(kw, args.examples)
            if ex:
                print(ex)


if __name__ == "__main__":
    main()
