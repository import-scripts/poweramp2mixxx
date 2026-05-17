from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from . import importer, mixxx, poweramp, reports

LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR"}


def add_common_import_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--poweramp", required=True, type=Path, help="Poweramp SQLite export path")
    parser.add_argument("--mixxx", required=True, type=Path, help="Mixxx mixxxdb.sqlite path")
    parser.add_argument(
        "--report-dir", type=Path, default=Path("./poweramp2mixxx-reports"), help="Directory for CSV reports"
    )
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing Mixxx ratings")
    parser.add_argument("--case-sensitive", action="store_true", help="Use case-sensitive filename matching")
    parser.add_argument(
        "--duration-tolerance",
        default=None,
        help="Reserved for future metadata matching; currently not implemented",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="poweramp2mixxx")
    parser.add_argument("--log-level", choices=sorted(LOG_LEVELS), default="INFO")
    subparsers = parser.add_subparsers(dest="command", required=True)

    pa = subparsers.add_parser("inspect-poweramp", help="Inspect a Poweramp SQLite export")
    pa.add_argument("database", type=Path)
    pa.set_defaults(func=cmd_inspect_poweramp)

    mx = subparsers.add_parser("inspect-mixxx", help="Inspect a Mixxx SQLite database")
    mx.add_argument("database", type=Path)
    mx.set_defaults(func=cmd_inspect_mixxx)

    dry = subparsers.add_parser("dry-run", help="Simulate rating import and write reports")
    add_common_import_options(dry)
    dry.set_defaults(func=cmd_dry_run)

    imp = subparsers.add_parser("import", help="Import ratings into Mixxx")
    add_common_import_options(imp)
    backup_group = imp.add_mutually_exclusive_group()
    backup_group.add_argument("--backup", dest="backup", action="store_true", default=True)
    backup_group.add_argument("--no-backup", dest="backup", action="store_false")
    imp.set_defaults(func=cmd_import)
    return parser


def _check_duration_tolerance(args: argparse.Namespace) -> None:
    if getattr(args, "duration_tolerance", None) is not None:
        raise ValueError("--duration-tolerance is reserved for future metadata matching and is not implemented")


def cmd_inspect_poweramp(args: argparse.Namespace) -> int:
    info = poweramp.inspect_database(args.database)
    print(f"Database: {info.database_path}")
    print(f"Tracks: {info.track_count}")
    print(f"Rated tracks: {info.rated_track_count}")
    print("Rating distribution:")
    for rating, count in sorted(info.rating_distribution.items()):
        print(f"  {rating}: {count}")
    print("Duplicate filenames among rated tracks:")
    if info.duplicate_filenames:
        for filename, count in sorted(info.duplicate_filenames.items()):
            print(f"  {filename}: {count}")
    else:
        print("  none")
    print("Invalid ratings:")
    if info.invalid_ratings:
        for rating, count in sorted(info.invalid_ratings.items()):
            print(f"  {rating}: {count}")
    else:
        print("  none")
    return 0


def cmd_inspect_mixxx(args: argparse.Namespace) -> int:
    info = mixxx.inspect_database(args.database)
    schema = info.schema
    print(f"Database: {info.database_path}")
    print(f"Detected tables: {', '.join(sorted(schema.tables))}")
    print(f"library exists: {schema.has_library}")
    print(f"track_locations exists: {schema.has_track_locations}")
    print(f"library.rating exists: {schema.has_library_rating}")
    print(f"track_locations.filename exists: {schema.has_track_locations_filename}")
    print(f"Tracks: {info.track_count}")
    print(f"Rated tracks: {info.rated_track_count}")
    return 0


def cmd_dry_run(args: argparse.Namespace) -> int:
    _check_duration_tolerance(args)
    summary = importer.dry_run(
        args.poweramp,
        args.mixxx,
        overwrite=args.overwrite,
        case_sensitive=args.case_sensitive,
    )
    reports.write_reports(args.report_dir, summary.results)
    text = reports.summary_text(summary.results)
    print(text, end="")
    print(f"Reports: {args.report_dir}")
    print("Dry run only; Mixxx database was not modified.")
    return 0


def cmd_import(args: argparse.Namespace) -> int:
    _check_duration_tolerance(args)
    if not args.backup:
        print("WARNING: --no-backup disables the safety backup before writing.", file=sys.stderr)
    summary = importer.import_ratings(
        args.poweramp,
        args.mixxx,
        overwrite=args.overwrite,
        backup=args.backup,
        case_sensitive=args.case_sensitive,
    )
    reports.write_reports(args.report_dir, summary.results, summary.backup_path)
    text = reports.summary_text(summary.results, summary.backup_path)
    print(text, end="")
    print(f"Reports: {args.report_dir}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(level=getattr(logging, args.log_level), format="%(levelname)s: %(message)s")
    try:
        return int(args.func(args))
    except (poweramp.PowerampError, mixxx.MixxxError, ValueError) as exc:
        logging.error("%s", exc)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
