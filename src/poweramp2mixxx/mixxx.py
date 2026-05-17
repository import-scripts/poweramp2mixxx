from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from .models import MixxxTrack


class MixxxError(RuntimeError):
    """Raised when a Mixxx database cannot be read or updated safely."""


@dataclass(frozen=True)
class MixxxSchema:
    tables: set[str]
    library_columns: set[str]
    track_locations_columns: set[str]
    has_library: bool
    has_track_locations: bool
    has_library_rating: bool
    has_track_locations_filename: bool
    has_deleted_flag: bool

    @property
    def supports_location_join(self) -> bool:
        return "location" in self.library_columns and "id" in self.track_locations_columns


@dataclass(frozen=True)
class MixxxInspection:
    database_path: Path
    schema: MixxxSchema
    track_count: int
    rated_track_count: int


def connect(path: Path, *, readonly: bool = True, timeout: float = 1.0) -> sqlite3.Connection:
    db_path = Path(path).expanduser().resolve()
    if not db_path.exists():
        raise MixxxError(f"Mixxx database does not exist: {db_path}")
    if readonly:
        uri = f"file:{db_path}?mode=ro"
        return sqlite3.connect(uri, uri=True, timeout=timeout)
    return sqlite3.connect(str(db_path), timeout=timeout)


def table_names(conn: sqlite3.Connection) -> set[str]:
    return {str(row[0]) for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def column_names(conn: sqlite3.Connection, table: str) -> set[str]:
    if table not in table_names(conn):
        return set()
    return {str(row[1]) for row in conn.execute(f"PRAGMA table_info({table})")}


def inspect_schema(conn: sqlite3.Connection) -> MixxxSchema:
    tables = table_names(conn)
    library_columns = column_names(conn, "library")
    track_locations_columns = column_names(conn, "track_locations")
    return MixxxSchema(
        tables=tables,
        library_columns=library_columns,
        track_locations_columns=track_locations_columns,
        has_library="library" in tables,
        has_track_locations="track_locations" in tables,
        has_library_rating="rating" in library_columns,
        has_track_locations_filename="filename" in track_locations_columns,
        has_deleted_flag="mixxx_deleted" in library_columns,
    )


def validate_schema(conn: sqlite3.Connection) -> MixxxSchema:
    schema = inspect_schema(conn)
    problems: list[str] = []
    if not schema.has_library:
        problems.append("missing library table")
    if not schema.has_track_locations:
        problems.append("missing track_locations table")
    if schema.has_library and not schema.has_library_rating:
        problems.append("missing library.rating column")
    if schema.has_track_locations and not schema.has_track_locations_filename:
        problems.append("missing track_locations.filename column")
    if schema.has_library and schema.has_track_locations and not schema.supports_location_join:
        problems.append("unsupported schema: expected library.location = track_locations.id join")
    if problems:
        raise MixxxError("Unsupported Mixxx database schema: " + "; ".join(problems))
    return schema


def read_tracks(conn: sqlite3.Connection) -> list[MixxxTrack]:
    schema = validate_schema(conn)
    where = "WHERE COALESCE(l.mixxx_deleted, 0) = 0" if schema.has_deleted_flag else ""
    rows = conn.execute(
        "SELECT l.id, l.rating, l.title, l.artist, tl.filename, tl.location "
        "FROM library l JOIN track_locations tl ON l.location = tl.id "
        f"{where} ORDER BY l.id"
    ).fetchall()
    return [
        MixxxTrack(
            id=int(row[0]),
            rating=int(row[1]) if row[1] is not None else None,
            title=row[2],
            artist=row[3],
            filename=str(row[4]) if row[4] is not None else "",
            location=row[5],
        )
        for row in rows
    ]


def inspect_database(path: Path) -> MixxxInspection:
    with connect(path, readonly=True) as conn:
        schema = validate_schema(conn)
        where = "WHERE COALESCE(mixxx_deleted, 0) = 0" if schema.has_deleted_flag else ""
        track_count = int(conn.execute(f"SELECT COUNT(*) FROM library {where}").fetchone()[0])
        rated_where = (
            "WHERE COALESCE(mixxx_deleted, 0) = 0 AND COALESCE(rating, 0) <> 0"
            if schema.has_deleted_flag
            else "WHERE COALESCE(rating, 0) <> 0"
        )
        rated_track_count = int(conn.execute(f"SELECT COUNT(*) FROM library {rated_where}").fetchone()[0])
        return MixxxInspection(Path(path).expanduser().resolve(), schema, track_count, rated_track_count)


def assert_writable(conn: sqlite3.Connection) -> None:
    try:
        conn.execute("PRAGMA query_only = OFF")
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("ROLLBACK")
    except sqlite3.Error as exc:
        raise MixxxError(f"Mixxx database cannot be opened safely for writing: {exc}") from exc
