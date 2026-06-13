#!/usr/bin/env python3
import argparse
import csv
import sys
import time
from pathlib import Path

from deep_translator import GoogleTranslator


DEFAULT_LANGUAGES = [
    ("French", "fr"),
    ("Botanical Latin", "la"),
    ("Spanish", "es"),
    ("German", "de"),
    ("Turkish", "tr"),
    ("Portuguese", "pt"),
]


def parse_languages(raw: str):
    if not raw.strip():
        return DEFAULT_LANGUAGES
    result = []
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        if ":" in item:
            name, code = item.split(":", 1)
            result.append((name.strip(), code.strip()))
        else:
            code = item
            result.append((code, code))
    return result


def print_progress(done: int, total: int, start_time: float):
    if total <= 0:
        return
    pct = (done / total) * 100
    elapsed = max(time.time() - start_time, 1e-6)
    rate = done / elapsed
    remaining = (total - done) / rate if rate > 0 else 0.0
    print(
        f"[progress] {done}/{total} ({pct:.2f}%) | "
        f"{rate:.2f} rows/s | eta {remaining:.1f}s",
        flush=True,
    )


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Translate CSV rows by expanding each source row with translated "
            "pattern rows and print live progress."
        )
    )
    parser.add_argument("--input", required=True, help="Input CSV file path")
    parser.add_argument(
        "--output",
        help=(
            "Output CSV file path. If omitted, writes to input path (in-place)."
        ),
    )
    parser.add_argument(
        "--languages",
        default="",
        help=(
            "Comma-separated language definitions: "
            "name:code,name:code (default is fixed 6-language set)."
        ),
    )
    parser.add_argument(
        "--source-lang",
        default="en",
        help="Source language code for patterns (default: en).",
    )
    parser.add_argument(
        "--pattern-column",
        default="pattern",
        help="CSV column to translate (default: pattern).",
    )
    parser.add_argument(
        "--progress-every",
        type=int,
        default=100,
        help="Print progress every N translation operations (default: 100).",
    )
    parser.add_argument(
        "--sleep-ms",
        type=float,
        default=20.0,
        help="Sleep milliseconds between API calls to reduce throttling.",
    )
    args = parser.parse_args()

    in_path = Path(args.input)
    out_path = Path(args.output) if args.output else in_path
    langs = parse_languages(args.languages)
    progress_every = max(args.progress_every, 1)
    sleep_sec = max(args.sleep_ms, 0.0) / 1000.0

    if not in_path.exists():
        print(f"Input file not found: {in_path}", file=sys.stderr)
        sys.exit(1)

    with in_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        rows = list(reader)

    if args.pattern_column not in fieldnames:
        print(
            f"Pattern column '{args.pattern_column}' not in CSV fields: {fieldnames}",
            file=sys.stderr,
        )
        sys.exit(1)

    translators = {
        code: GoogleTranslator(source=args.source_lang, target=code)
        for _, code in langs
    }
    cache = {}
    expanded_rows = []

    original_rows = len(rows)
    total_ops = original_rows * len(langs)
    done_ops = 0
    added_rows = 0
    start_time = time.time()

    print(
        f"Starting translation: rows={original_rows}, languages={len(langs)}, "
        f"operations={total_ops}",
        flush=True,
    )

    for row in rows:
        base = {k: row.get(k, "") for k in fieldnames}
        expanded_rows.append(base)

        source_text = base.get(args.pattern_column, "") or ""
        for _, code in langs:
            key = (source_text, code)
            if key in cache:
                translated = cache[key]
            elif source_text == "":
                translated = ""
                cache[key] = translated
            else:
                translated = translators[code].translate(source_text) or ""
                cache[key] = translated
                if sleep_sec > 0:
                    time.sleep(sleep_sec)

            candidate = dict(base)
            candidate[args.pattern_column] = translated

            # Deduplicate exact adjacent duplicates only.
            if expanded_rows and candidate == expanded_rows[-1]:
                done_ops += 1
                if done_ops % progress_every == 0 or done_ops == total_ops:
                    print_progress(done_ops, total_ops, start_time)
                continue

            expanded_rows.append(candidate)
            added_rows += 1

            done_ops += 1
            if done_ops % progress_every == 0 or done_ops == total_ops:
                print_progress(done_ops, total_ops, start_time)

    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(expanded_rows)

    final_rows = len(expanded_rows)
    print("Completed.", flush=True)
    print(f"original_rows={original_rows}", flush=True)
    print(f"added_rows={added_rows}", flush=True)
    print(f"final_rows={final_rows}", flush=True)


if __name__ == "__main__":
    main()
