from __future__ import annotations

import sqlite3
from pathlib import Path


def create_poweramp_db(path: Path, rows: list[tuple[int, str, str | None, int]]) -> Path:
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE tracks (_id INTEGER PRIMARY KEY, path TEXT NOT NULL, readable_name TEXT, rating INTEGER)"
    )
    conn.executemany("INSERT INTO tracks (_id, path, readable_name, rating) VALUES (?, ?, ?, ?)", rows)
    conn.commit()
    conn.close()
    return path


def create_mixxx_db(
    path: Path,
    rows: list[tuple[int, int, str, str | None, str | None, str | None, int | None]],
    *,
    deleted_column: bool = True,
) -> Path:
    conn = sqlite3.connect(path)
    deleted = ", mixxx_deleted INTEGER DEFAULT 0" if deleted_column else ""
    conn.execute(
        f"CREATE TABLE library (id INTEGER PRIMARY KEY, location INTEGER, rating INTEGER DEFAULT 0, title TEXT, artist TEXT{deleted})"
    )
    conn.execute("CREATE TABLE track_locations (id INTEGER PRIMARY KEY, filename TEXT, location TEXT)")
    for lib_id, loc_id, filename, location, title, artist, rating in rows:
        conn.execute(
            "INSERT INTO track_locations (id, filename, location) VALUES (?, ?, ?)",
            (loc_id, filename, location),
        )
        if deleted_column:
            conn.execute(
                "INSERT INTO library (id, location, rating, title, artist, mixxx_deleted) VALUES (?, ?, ?, ?, ?, 0)",
                (lib_id, loc_id, rating, title, artist),
            )
        else:
            conn.execute(
                "INSERT INTO library (id, location, rating, title, artist) VALUES (?, ?, ?, ?, ?)",
                (lib_id, loc_id, rating, title, artist),
            )
    conn.commit()
    conn.close()
    return path


def get_rating(path: Path, library_id: int) -> int | None:
    conn = sqlite3.connect(path)
    row = conn.execute("SELECT rating FROM library WHERE id = ?", (library_id,)).fetchone()
    conn.close()
    return row[0]
