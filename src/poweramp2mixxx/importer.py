from __future__ import annotations

import shutil
import sqlite3
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from . import mixxx, poweramp
from .matcher import match_tracks
from .models import STATUS_IMPORTABLE, STATUS_IMPORTED, STATUS_ERROR, MatchResult


@dataclass(frozen=True)
class ImportSummary:
    results: list[MatchResult]
    backup_path: Path | None

    @property
    def counts(self) -> dict[str, int]:
        return dict(Counter(result.status for result in self.results))


def create_backup(database_path: Path) -> Path:
    source = Path(database_path).expanduser().resolve()
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup = source.with_name(f"{source.name}.{timestamp}.bak")
    shutil.copy2(source, backup)
    return backup


def dry_run(
    poweramp_path: Path,
    mixxx_path: Path,
    *,
    overwrite: bool = False,
    case_sensitive: bool = False,
) -> ImportSummary:
    with poweramp.connect_readonly(poweramp_path) as poweramp_conn, mixxx.connect(mixxx_path, readonly=True) as mixxx_conn:
        poweramp_tracks = poweramp.read_rated_tracks(poweramp_conn)
        mixxx_tracks = mixxx.read_tracks(mixxx_conn)
    results = match_tracks(
        poweramp_tracks, mixxx_tracks, overwrite=overwrite, case_sensitive=case_sensitive
    )
    return ImportSummary(results=results, backup_path=None)


def import_ratings(
    poweramp_path: Path,
    mixxx_path: Path,
    *,
    overwrite: bool = False,
    backup: bool = True,
    case_sensitive: bool = False,
) -> ImportSummary:
    summary = dry_run(
        poweramp_path, mixxx_path, overwrite=overwrite, case_sensitive=case_sensitive
    )
    db_path = Path(mixxx_path).expanduser().resolve()
    backup_path = create_backup(db_path) if backup else None
    conn = mixxx.connect(db_path, readonly=False, timeout=1.0)
    results: list[MatchResult] = []
    try:
        mixxx.validate_schema(conn)
        conn.execute("BEGIN IMMEDIATE")
        for result in summary.results:
            if result.status != STATUS_IMPORTABLE or result.mixxx_track is None:
                results.append(result)
                continue
            if overwrite:
                cur = conn.execute(
                    "UPDATE library SET rating = ? WHERE id = ?",
                    (result.poweramp_track.rating, result.mixxx_track.id),
                )
            else:
                cur = conn.execute(
                    "UPDATE library SET rating = ? WHERE id = ? AND COALESCE(rating, 0) = 0",
                    (result.poweramp_track.rating, result.mixxx_track.id),
                )
            if cur.rowcount == 1:
                results.append(
                    MatchResult(result.poweramp_track, result.mixxx_track, STATUS_IMPORTED, "Rating imported")
                )
            else:
                results.append(
                    MatchResult(result.poweramp_track, result.mixxx_track, STATUS_ERROR, "Update affected no rows")
                )
        conn.commit()
    except sqlite3.Error as exc:
        conn.rollback()
        raise mixxx.MixxxError(f"Import failed; transaction rolled back: {exc}") from exc
    finally:
        conn.close()
    return ImportSummary(results=results, backup_path=backup_path)
