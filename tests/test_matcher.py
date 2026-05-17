from __future__ import annotations

from poweramp2mixxx.matcher import match_tracks
from poweramp2mixxx.models import (
    STATUS_AMBIGUOUS_MIXXX,
    STATUS_IMPORTABLE,
    STATUS_INVALID_RATING,
    STATUS_SKIPPED_EXISTING,
    STATUS_UNMATCHED,
    MixxxTrack,
    PowerampTrack,
)


def pa(name: str, rating: int = 5) -> PowerampTrack:
    return PowerampTrack(1, f"/music/{name}", name, None, rating)


def mx(name: str, rating: int | None = 0, id_: int = 1) -> MixxxTrack:
    return MixxxTrack(id_, name, f"/music/{name}", rating, None, None)


def test_exact_unique_filename_match():
    assert match_tracks([pa("Song.flac")], [mx("Song.flac")])[0].status == STATUS_IMPORTABLE


def test_case_insensitive_match_default_and_case_sensitive_option():
    assert match_tracks([pa("Song.flac")], [mx("song.flac")])[0].status == STATUS_IMPORTABLE
    assert match_tracks([pa("Song.flac")], [mx("song.flac")], case_sensitive=True)[0].status == STATUS_UNMATCHED


def test_skip_existing_and_overwrite():
    assert match_tracks([pa("Song.flac")], [mx("Song.flac", 3)])[0].status == STATUS_SKIPPED_EXISTING
    assert match_tracks([pa("Song.flac")], [mx("Song.flac", 3)], overwrite=True)[0].status == STATUS_IMPORTABLE


def test_ambiguous_mixxx_unmatched_and_invalid_rating():
    assert match_tracks([pa("Song.flac")], [mx("Song.flac", id_=1), mx("Song.flac", id_=2)])[0].status == STATUS_AMBIGUOUS_MIXXX
    assert match_tracks([pa("Missing.flac")], [mx("Song.flac")])[0].status == STATUS_UNMATCHED
    assert match_tracks([pa("Song.flac", 9)], [mx("Song.flac")])[0].status == STATUS_INVALID_RATING
