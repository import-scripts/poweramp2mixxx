from __future__ import annotations

import sqlite3

import pytest

from poweramp2mixxx import mixxx
from conftest import create_mixxx_db


def test_mixxx_schema_validation(tmp_path):
    db = tmp_path / "mixxx.sqlite"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE library (id INTEGER PRIMARY KEY, location INTEGER)")
    conn.execute("CREATE TABLE track_locations (id INTEGER PRIMARY KEY, filename TEXT)")
    conn.commit(); conn.close()
    with mixxx.connect(db, readonly=True) as conn, pytest.raises(mixxx.MixxxError, match="library.rating"):
        mixxx.validate_schema(conn)


def test_mixxx_inspection_and_read_tracks(tmp_path):
    db = create_mixxx_db(tmp_path / "mixxx.sqlite", [
        (1, 10, "Song.flac", "/music/Song.flac", "Song", "Artist", 0),
        (2, 20, "Rated.flac", "/music/Rated.flac", "Rated", "Artist", 4),
    ])
    info = mixxx.inspect_database(db)
    assert info.track_count == 2
    assert info.rated_track_count == 1
    with mixxx.connect(db) as conn:
        tracks = mixxx.read_tracks(conn)
    assert tracks[0].filename == "Song.flac"
