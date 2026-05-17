from __future__ import annotations

from poweramp2mixxx import importer
from conftest import create_mixxx_db, create_poweramp_db, get_rating


def test_dry_run_does_not_modify_mixxx(tmp_path):
    pa = create_poweramp_db(tmp_path / "pa.sqlite", [(1, "/music/Song.flac", None, 5)])
    mx = create_mixxx_db(tmp_path / "mixxx.sqlite", [(1, 10, "Song.flac", "/music/Song.flac", None, None, 0)])
    summary = importer.dry_run(pa, mx)
    assert summary.counts == {"importable": 1}
    assert get_rating(mx, 1) == 0


def test_import_modifies_only_importable_rows_and_creates_backup(tmp_path):
    pa = create_poweramp_db(tmp_path / "pa.sqlite", [
        (1, "/music/Song.flac", None, 5),
        (2, "/music/Rated.flac", None, 2),
        (3, "/music/Missing.flac", None, 4),
    ])
    mx = create_mixxx_db(tmp_path / "mixxx.sqlite", [
        (1, 10, "Song.flac", "/music/Song.flac", None, None, 0),
        (2, 20, "Rated.flac", "/music/Rated.flac", None, None, 3),
    ])
    summary = importer.import_ratings(pa, mx)
    assert summary.backup_path is not None
    assert summary.backup_path.exists()
    assert get_rating(mx, 1) == 5
    assert get_rating(mx, 2) == 3


def test_import_overwrite_existing_rating(tmp_path):
    pa = create_poweramp_db(tmp_path / "pa.sqlite", [(1, "/music/Rated.flac", None, 2)])
    mx = create_mixxx_db(tmp_path / "mixxx.sqlite", [(1, 10, "Rated.flac", "/music/Rated.flac", None, None, 3)])
    importer.import_ratings(pa, mx, overwrite=True, backup=False)
    assert get_rating(mx, 1) == 2
