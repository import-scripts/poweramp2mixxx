# poweramp2mixxx

![poweramp2mixxx Banner](assets/poweramp2mixxx-banner.png)

`poweramp2mixxx` is a small Python command-line tool that imports star ratings
from a Poweramp SQLite export into an existing Mixxx `mixxxdb.sqlite` database.

It is intentionally conservative:

- **Dry run is the default workflow.** The `dry-run` command never writes to
  Mixxx.
- The tool **does not import tracks** into Mixxx. It only updates ratings for
  tracks already present in the Mixxx library.
- Version 0.1 matches tracks **by filename only**: the filename extracted from
  Poweramp `tracks.path` is compared with Mixxx `track_locations.filename`.
- Ambiguous filenames are **never imported automatically**.
- Existing Mixxx ratings are preserved unless `--overwrite` is explicitly used.
- Imports create a timestamped database backup by default.

## Installation

From a checkout of this repository:

```bash
python -m pip install .
```

If your system uses an externally managed Python environment (PEP 668), install
in a local virtual environment instead:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install .
```

The package installs the console command:

```bash
poweramp2mixxx --help
```

With a local virtual environment, run:

```bash
.venv/bin/poweramp2mixxx --help
```

You can also run it from source with:

```bash
PYTHONPATH=src python -m poweramp2mixxx --help
```

## Matching behavior

Poweramp stores Android/Linux-like paths such as:

```text
/storage/0000-0000/Music/Ark Goa/096 - Elegy - Hush.flac
```

`poweramp2mixxx` extracts only the filename:

```text
096 - Elegy - Hush.flac
```

and compares it to Mixxx `track_locations.filename`.

By default matching is case-insensitive after trimming whitespace. Pass
`--case-sensitive` to require exact filename casing.

A rating is importable only when:

1. the Poweramp rating is in `1..5`;
2. the Poweramp filename is not empty;
3. that filename is unique among rated Poweramp tracks;
4. exactly one non-deleted Mixxx library row has the same filename;
5. the Mixxx rating is empty (`NULL` or `0`), unless `--overwrite` is used; and
6. the Mixxx database can be opened safely for writing during `import`.

## Commands

### Inspect a Poweramp export

```bash
poweramp2mixxx inspect-poweramp ./lists-export
```

Prints:

- database path;
- total track count;
- rated track count;
- rating distribution;
- duplicate filenames among rated tracks; and
- invalid ratings.

### Inspect a Mixxx database

```bash
poweramp2mixxx inspect-mixxx ~/.mixxx/mixxxdb.sqlite
```

Prints detected tables, required schema support, track count, and rated track
count. The Mixxx schema is inspected at runtime. The current release supports
the standard join `library.location = track_locations.id` and refuses unsupported
schemas.

### Dry run

```bash
poweramp2mixxx dry-run \
  --poweramp ./lists-export \
  --mixxx ~/.mixxx/mixxxdb.sqlite \
  --report-dir ./reports
```

This reads both databases, simulates rating updates, writes reports, prints a
summary, and does **not** modify Mixxx.

### Import

```bash
poweramp2mixxx import \
  --poweramp ./lists-export \
  --mixxx ~/.mixxx/mixxxdb.sqlite \
  --report-dir ./reports \
  --backup
```

`import` performs the same matching as `dry-run`, then updates only importable
Mixxx rows inside a transaction. A timestamped backup such as
`mixxxdb.sqlite.20260517-121314.bak` is created before writing unless
`--no-backup` is passed.

Use `--overwrite` to replace existing Mixxx ratings:

```bash
poweramp2mixxx import --poweramp ./lists-export --mixxx ~/.mixxx/mixxxdb.sqlite --overwrite
```

Without `--overwrite`, existing Mixxx ratings are skipped.

## Options

- `--overwrite` — overwrite existing Mixxx ratings.
- `--backup` — create a backup before writing. This is the default for `import`.
- `--no-backup` — disable the import backup and print a warning.
- `--case-sensitive` — use case-sensitive filename matching.
- `--report-dir PATH` — report output directory. Default:
  `./poweramp2mixxx-reports`.
- `--log-level LEVEL` — `DEBUG`, `INFO`, `WARNING`, or `ERROR`.
- `--duration-tolerance` — reserved for future metadata matching and currently
  not implemented.

## Reports

Reports are UTF-8 CSV files plus a text summary:

- `matched.csv`
- `imported.csv`
- `skipped_existing_ratings.csv`
- `ambiguous_poweramp_filenames.csv`
- `ambiguous_mixxx_filenames.csv`
- `unmatched.csv`
- `invalid_ratings.csv`
- `summary.txt`

CSV columns:

```text
poweramp_id,poweramp_path,poweramp_filename,poweramp_readable_name,poweramp_rating,mixxx_id,mixxx_filename,mixxx_location,mixxx_title,mixxx_artist,mixxx_old_rating,status,reason
```

## Safety notes

Close Mixxx before running `import`. If the database is locked or the supported
schema cannot be verified, the import refuses to write. All updates happen in a
transaction and are rolled back on SQLite errors.

## Roadmap

Future versions may add metadata matching, duration tolerance, and optional tag
writing such as FMPS_RATING or POPM. These are intentionally not implemented in
this first version.

## License

GPL-2.0-or-later. See [LICENSE](LICENSE).
