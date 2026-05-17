from __future__ import annotations

import sqlite3
from collections import Counter
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from .models import PowerampTrack


class PowerampError(RuntimeError):
    """Raised when a Poweramp export cannot be read safely."""


REQUIRED_TRACK_COLUMNS = {"_id", "path", "rating"}


@dataclass(frozen=True)
class PowerampInspection:
    database_path: Path
    track_count: int
    rated_track_count: int
    rating_distribution: dict[int, int]
    duplicate_filenames: dict[str, int]
    invalid_ratings: dict[int, int]


def connect_readonly(path: Path) -> sqlite3.Connection:
    db_path = Path(path).expanduser().resolve()
    if not db_path.exists():
        raise PowerampError(f"Poweramp database does not exist: {db_path}")
    uri = f"file:{db_path}?mode=ro"
    return sqlite3.connect(uri, uri=True)


def extract_filename(path: str) -> str:
    return PurePosixPath(path or "").name


def table_names(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    return {str(row[0]) for row in rows}


def column_names(conn: sqlite3.Connection, table: str) -> set[str]:
    return {str(row[1]) for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def validate_schema(conn: sqlite3.Connection) -> None:
    if "tracks" not in table_names(conn):
        raise PowerampError("Unsupported Poweramp export: missing tracks table")
    missing = REQUIRED_TRACK_COLUMNS - column_names(conn, "tracks")
    if missing:
        raise PowerampError(
            "Unsupported Poweramp export: tracks table missing required columns: "
            + ", ".join(sorted(missing))
        )


def read_rated_tracks(conn: sqlite3.Connection) -> list[PowerampTrack]:
    validate_schema(conn)
    rows = conn.execute(
        "SELECT _id, path, readable_name, rating FROM tracks WHERE rating > 0 ORDER BY _id"
    ).fetchall()
    return [
        PowerampTrack(
            id=int(row[0]),
            path=str(row[1]),
            filename=extract_filename(str(row[1])),
            readable_name=row[2],
            rating=int(row[3]) if row[3] is not None else 0,
        )
        for row in rows
    ]


def duplicate_filenames(tracks: list[PowerampTrack], *, case_sensitive: bool = False) -> dict[str, int]:
    counts: Counter[str] = Counter()
    display: dict[str, str] = {}
    for track in tracks:
        name = track.filename.strip()
        key = name if case_sensitive else name.lower()
        if key:
            counts[key] += 1
            display.setdefault(key, name)
    return {display[key]: count for key, count in counts.items() if count > 1}


def inspect_database(path: Path) -> PowerampInspection:
    with connect_readonly(path) as conn:
        validate_schema(conn)
        track_count = int(conn.execute("SELECT COUNT(*) FROM tracks").fetchone()[0])
        rated_track_count = int(
            conn.execute("SELECT COUNT(*) FROM tracks WHERE rating > 0").fetchone()[0]
        )
        rating_distribution = {
            int(rating): int(count)
            for rating, count in conn.execute(
                "SELECT rating, COUNT(*) FROM tracks GROUP BY rating ORDER BY rating"
            ).fetchall()
            if rating is not None
        }
        invalid_ratings = {
            int(rating): int(count)
            for rating, count in conn.execute(
                "SELECT rating, COUNT(*) FROM tracks "
                "WHERE rating IS NOT NULL AND rating NOT BETWEEN 0 AND 5 "
                "GROUP BY rating ORDER BY rating"
            ).fetchall()
        }
        tracks = read_rated_tracks(conn)
        duplicates = duplicate_filenames(tracks)
        return PowerampInspection(
            database_path=Path(path).expanduser().resolve(),
            track_count=track_count,
            rated_track_count=rated_track_count,
            rating_distribution=rating_distribution,
            duplicate_filenames=duplicates,
            invalid_ratings=invalid_ratings,
        )
