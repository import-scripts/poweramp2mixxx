from __future__ import annotations

from collections import Counter, defaultdict

from .models import (
    STATUS_AMBIGUOUS_MIXXX,
    STATUS_AMBIGUOUS_POWERAMP,
    STATUS_IMPORTABLE,
    STATUS_INVALID_RATING,
    STATUS_SKIPPED_EXISTING,
    STATUS_UNMATCHED,
    MatchResult,
    MixxxTrack,
    PowerampTrack,
)


def normalize_filename(filename: str, *, case_sensitive: bool = False) -> str:
    name = filename.strip()
    return name if case_sensitive else name.lower()


def duplicate_poweramp_keys(
    tracks: list[PowerampTrack], *, case_sensitive: bool = False
) -> set[str]:
    counts: Counter[str] = Counter(
        normalize_filename(track.filename, case_sensitive=case_sensitive)
        for track in tracks
        if track.rating > 0 and normalize_filename(track.filename, case_sensitive=case_sensitive)
    )
    return {key for key, count in counts.items() if count > 1}


def match_tracks(
    poweramp_tracks: list[PowerampTrack],
    mixxx_tracks: list[MixxxTrack],
    *,
    overwrite: bool = False,
    case_sensitive: bool = False,
) -> list[MatchResult]:
    mixxx_index: dict[str, list[MixxxTrack]] = defaultdict(list)
    for track in mixxx_tracks:
        key = normalize_filename(track.filename, case_sensitive=case_sensitive)
        if key:
            mixxx_index[key].append(track)

    poweramp_duplicates = duplicate_poweramp_keys(poweramp_tracks, case_sensitive=case_sensitive)
    results: list[MatchResult] = []
    for track in poweramp_tracks:
        key = normalize_filename(track.filename, case_sensitive=case_sensitive)
        if track.rating not in range(1, 6):
            results.append(MatchResult(track, None, STATUS_INVALID_RATING, "Poweramp rating is not in 1..5"))
            continue
        if not key:
            results.append(MatchResult(track, None, STATUS_UNMATCHED, "Poweramp filename is empty"))
            continue
        if key in poweramp_duplicates:
            results.append(
                MatchResult(track, None, STATUS_AMBIGUOUS_POWERAMP, "Filename is duplicated among rated Poweramp tracks")
            )
            continue
        matches = mixxx_index.get(key, [])
        if not matches:
            results.append(MatchResult(track, None, STATUS_UNMATCHED, "No Mixxx track has the same filename"))
            continue
        if len(matches) > 1:
            results.append(
                MatchResult(track, None, STATUS_AMBIGUOUS_MIXXX, "More than one Mixxx track has the same filename")
            )
            continue
        mixxx_track = matches[0]
        if not overwrite and mixxx_track.rating not in (None, 0):
            results.append(
                MatchResult(track, mixxx_track, STATUS_SKIPPED_EXISTING, "Mixxx track already has a rating")
            )
            continue
        results.append(MatchResult(track, mixxx_track, STATUS_IMPORTABLE, "Safe filename match"))
    return results
