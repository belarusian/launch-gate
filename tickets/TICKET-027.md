# TICKET-027: pin wall-sizing (p) — fourseer row robustness

## Evidence
`durations_from_fourseer` in `launch_gate/wall_sizing.py` matches each row with
`_FOURSEER_ROW_RE`, whose Steps cell is `(\d+|-)` and whose Duration cell is
`(\d+|-)`. A row is kept only when the Duration cell is numeric. Verified at
runtime (Cycle 9):
- a row whose Steps cell is a dash (`-`) is kept as long as the Duration cell is
  numeric: `| 7 | x | - | 1358 | t.json |` -> `[1358]`.
- a row with a trailing extra cell is tolerated (the regex is anchored at the
  start and does not require the line to end at the last cell):
  `| 7 | x | 41 | 1358 | t.json | extra |` -> `[1358]`.

The seed dialect uses `-` for a no-observation Steps/Duration cell, so the dash
Steps cell is the real-world "non-numeric" case. Neither behavior is pinned.

## Impact
A regression in the row regex (e.g. requiring the Steps cell to be numeric, or
anchoring the match to the end of the line) would silently drop observed
durations and flip a sizing verdict. Pinning both keeps the parser honest about
the seed dialect.

## Suggestion
Add two parser unit tests in `tests/test_wall_sizing.py` (no `tmp_path` needed):
- a row with a dash Steps cell and a numeric Duration -> `[1358]`.
- a row with a trailing extra cell -> `[1358]`.
