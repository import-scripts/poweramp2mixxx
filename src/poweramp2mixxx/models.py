from __future__ import annotations

from dataclasses import dataclass


STATUS_IMPORTABLE = "importable"
STATUS_IMPORTED = "imported"
STATUS_SKIPPED_EXISTING = "skipped_existing_rating"
STATUS_AMBIGUOUS_POWERAMP = "ambiguous_poweramp_filename"
STATUS_AMBIGUOUS_MIXXX = "ambiguous_mixxx_filename"
STATUS_UNMATCHED = "unmatched"
STATUS_INVALID_RATING = "invalid_rating"
STATUS_ERROR = "error"


@dataclass(frozen=True)
class PowerampTrack:
    id: int
    path: str
    filename: str
    readable_name: str | None
    rating: int


@dataclass(frozen=True)
class MixxxTrack:
    id: int
    filename: str
    location: str | None
    rating: int | None
    title: str | None
    artist: str | None


@dataclass(frozen=True)
class MatchResult:
    poweramp_track: PowerampTrack
    mixxx_track: MixxxTrack | None
    status: str
    reason: str
