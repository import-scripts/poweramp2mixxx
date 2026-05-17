from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

from .models import (
    STATUS_AMBIGUOUS_MIXXX,
    STATUS_AMBIGUOUS_POWERAMP,
    STATUS_IMPORTED,
    STATUS_IMPORTABLE,
    STATUS_INVALID_RATING,
    STATUS_SKIPPED_EXISTING,
    STATUS_UNMATCHED,
    MatchResult,
)

HEADER = [
    "poweramp_id",
    "poweramp_path",
    "poweramp_filename",
    "poweramp_readable_name",
    "poweramp_rating",
    "mixxx_id",
    "mixxx_filename",
    "mixxx_location",
    "mixxx_title",
    "mixxx_artist",
    "mixxx_old_rating",
    "status",
    "reason",
]

REPORTS = {
    "matched.csv": {STATUS_IMPORTABLE, STATUS_IMPORTED, STATUS_SKIPPED_EXISTING},
    "imported.csv": {STATUS_IMPORTED},
    "skipped_existing_ratings.csv": {STATUS_SKIPPED_EXISTING},
    "ambiguous_poweramp_filenames.csv": {STATUS_AMBIGUOUS_POWERAMP},
    "ambiguous_mixxx_filenames.csv": {STATUS_AMBIGUOUS_MIXXX},
    "unmatched.csv": {STATUS_UNMATCHED},
    "invalid_ratings.csv": {STATUS_INVALID_RATING},
}


def row_for(result: MatchResult) -> list[object | None]:
    pa = result.poweramp_track
    mx = result.mixxx_track
    return [
        pa.id,
        pa.path,
        pa.filename,
        pa.readable_name,
        pa.rating,
        mx.id if mx else None,
        mx.filename if mx else None,
        mx.location if mx else None,
        mx.title if mx else None,
        mx.artist if mx else None,
        mx.rating if mx else None,
        result.status,
        result.reason,
    ]


def write_csv(path: Path, results: list[MatchResult]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(HEADER)
        for result in results:
            writer.writerow(row_for(result))


def summary_text(results: list[MatchResult], backup_path: Path | None = None) -> str:
    counts = Counter(result.status for result in results)
    lines = ["poweramp2mixxx summary", "", f"Total rated Poweramp rows considered: {len(results)}"]
    for status in sorted(counts):
        lines.append(f"{status}: {counts[status]}")
    if backup_path is not None:
        lines.append(f"Backup: {backup_path}")
    return "\n".join(lines) + "\n"


def write_reports(report_dir: Path, results: list[MatchResult], backup_path: Path | None = None) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    for filename, statuses in REPORTS.items():
        write_csv(report_dir / filename, [result for result in results if result.status in statuses])
    (report_dir / "summary.txt").write_text(summary_text(results, backup_path), encoding="utf-8")
