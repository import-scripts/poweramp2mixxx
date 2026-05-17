from __future__ import annotations

import sqlite3

import pytest

from poweramp2mixxx import poweramp
from conftest import create_poweramp_db


def test_tracks_table_missing_error(tmp_path):
    db = tmp_path / "pa.sqlite"
    sqlite3.connect(db).close()
    with poweramp.connect_readonly(db) as conn, pytest.raises(poweramp.PowerampError, match="missing tracks"):
        poweramp.validate_schema(conn)


def test_required_columns_missing_error(tmp_path):
    db = tmp_path / "pa.sqlite"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE tracks (_id INTEGER PRIMARY KEY, path TEXT)")
    conn.commit(); conn.close()
    with poweramp.connect_readonly(db) as conn, pytest.raises(poweramp.PowerampError, match="rating"):
        poweramp.validate_schema(conn)


def test_rating_distribution_filename_extraction_and_duplicates(tmp_path):
    db = create_poweramp_db(tmp_path / "pa.sqlite", [
        (1, "/storage/0000/Music/096 - Elegy - Hush.flac", "Hush", 5),
        (2, "/storage/0000/Other/096 - Elegy - Hush.flac", "Hush again", 4),
        (3, "/storage/0000/Music/Other.mp3", "Other", 0),
        (4, "/storage/0000/Music/Bad.mp3", "Bad", 7),
    ])
    assert poweramp.extract_filename("/storage/0000/Music/096 - Elegy - Hush.flac") == "096 - Elegy - Hush.flac"
    info = poweramp.inspect_database(db)
    assert info.rating_distribution == {0: 1, 4: 1, 5: 1, 7: 1}
    assert info.invalid_ratings == {7: 1}
    assert info.duplicate_filenames == {"096 - Elegy - Hush.flac": 2}
