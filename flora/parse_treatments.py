#!/usr/bin/env python3
import argparse
import logging
import textwrap
from pathlib import Path

from flora.pylib import const, log
from flora.pylib.treatments import Treatments
from flora.pylib.writers.csv_writer import write_csv
from flora.pylib.writers.html_writer import HtmlWriter
from flora.pylib.writers.json_writer import write_json


def main():
    log.started()
    args = parse_args()

    batch_dirs = _batch_dirs(args.treatment_dir)
    batch_dirs = _slice_batches_from(batch_dirs, args.start_batch)
    single_batch = len(batch_dirs) == 1 and batch_dirs[0] == args.treatment_dir

    for i, batch_dir in enumerate(batch_dirs, start=1):
        logging.info(
            "Processing batch %d/%d: %s",
            i,
            len(batch_dirs),
            batch_dir.resolve(),
        )
        treatments: Treatments = Treatments(
            batch_dir, args.limit, args.offset, args.parse_timeout
        )
        treatments.parse(encoding=args.encoding)

        html_path = (
            args.html_file
            if (single_batch and args.html_file)
            else _batch_output_path(args.html_file, batch_dir, ".html")
        )
        if html_path:
            html_path.parent.mkdir(parents=True, exist_ok=True)
            writer = HtmlWriter(
                template_dir=f"{const.ROOT_DIR}/flora/pylib/writers/templates",
                template="treatment_html_writer.html",
                html_file=html_path,
                spotlight=args.spotlight,
            )
            writer.write(treatments, args)

        csv_path = (
            args.csv_file
            if (single_batch and args.csv_file)
            else _batch_output_path(args.csv_file, batch_dir, ".csv")
        )
        if csv_path:
            csv_path.parent.mkdir(parents=True, exist_ok=True)
            write_csv(treatments, csv_path)

        if args.json_dir:
            json_batch_dir = (
                args.json_dir
                if single_batch
                else args.json_dir / batch_dir.name
            )
            json_batch_dir.mkdir(parents=True, exist_ok=True)
            write_json(treatments, json_batch_dir)

    log.finished()


def _batch_dirs(treatment_dir: Path) -> list[Path]:
    """If treatment_dir contains only subdirectories, return them as batches; else treat the dir itself as one batch."""
    subdirs = sorted(p for p in treatment_dir.iterdir() if p.is_dir())
    if subdirs:
        return subdirs
    return [treatment_dir]


def _slice_batches_from(batch_dirs: list[Path], start_batch: str | None) -> list[Path]:
    """Keep batches from the first whose name matches ``start_batch`` onward (sorted order)."""
    if not start_batch:
        return batch_dirs
    names = [p.name for p in batch_dirs]
    try:
        idx = names.index(start_batch)
    except ValueError:
        raise SystemExit(
            f"--start-batch {start_batch!r} not found under treatment dir. "
            f"Available batch folder names ({len(names)}): {', '.join(names)}",
        ) from None
    return batch_dirs[idx:]


def _batch_output_path(output_file: Path | None, batch_dir: Path, suffix: str) -> Path | None:
    """Per-batch output path: same parent as output_file, filename is batch_dir.name + suffix."""
    if output_file is None:
        return None
    return output_file.parent / f"{batch_dir.name}{suffix}"


def parse_args() -> argparse.Namespace:
    arg_parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent(
            """
            Extract floral trait information from treatment text extracted
            from PDFs or web pages.
            """,
        ),
    )

    arg_parser.add_argument(
        "--treatment-dir",
        metavar="PATH",
        type=Path,
        required=True,
        help="""Directory containing the input treatment text files.""",
    )

    arg_parser.add_argument(
        "--start-batch",
        metavar="NAME",
        help="""When treatment-dir has batch subfolders (sorted by name), begin processing
            at the subfolder named NAME and continue with the rest. Ignored when
            treatment-dir is a single batch (no subfolders).""",
    )

    arg_parser.add_argument(
        "--html-file",
        type=Path,
        metavar="PATH",
        help="""Output HTML formatted results to this file.""",
    )

    arg_parser.add_argument(
        "--csv-file",
        type=Path,
        metavar="PATH",
        help="""Output results to this CSV file.""",
    )

    arg_parser.add_argument(
        "--json-dir",
        metavar="PATH",
        type=Path,
        help="""Output JSON files holding traits, one for each input text file, in this
            directory.""",
    )

    arg_parser.add_argument(
        "--limit",
        type=int,
        help="""Read this many treatments for input.""",
    )

    arg_parser.add_argument(
        "--offset",
        type=int,
        default=0,
        help="""Offset for splitting data.""",
    )

    arg_parser.add_argument(
        "--spotlight",
        metavar="TRAIT",
        help="""This trait will get its own color for HTML output.""",
    )

    arg_parser.add_argument(
        "--encoding",
        metavar="ENCODING",
        default="utf8",
        help="""What encoding is used for the input file. These should be Western
        European encodings; that's what the parsers are designed for.
        (default: %(default)s)""",
    )

    arg_parser.add_argument(
        "--parse-timeout",
        type=float,
        default=120.0,
        metavar="SECONDS",
        help="""Skip a treatment if parsing takes longer than this many seconds.
            The hung worker is killed and processing continues. Use 0 to disable.
            (default: %(default)s)""",
    )

    args = arg_parser.parse_args()
    if args.parse_timeout is not None and args.parse_timeout <= 0:
        args.parse_timeout = None
    return args


if __name__ == "__main__":
    main()
