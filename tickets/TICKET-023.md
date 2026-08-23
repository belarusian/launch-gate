# TICKET-023: pin the wall-sizing parsers (outer wall, inner-seconds, fourseer, cycles.out)

## Evidence
The four parsers in `launch_gate/wall_sizing.py` are the load-bearing seams of
check 3 and are not unit-tested in isolation:

- **`parse_outer_wall`** — extracts the `perl -e 'alarm shift; exec @ARGV' <N>`
  seconds from the driver script (the seed dialect); `None` when absent.
- **`parse_inner_seconds`** — extracts the `--inner-seconds <N>` value; `None`
  when absent.
- **`durations_from_fourseer`** — reads the 4th cell (Duration (s)) of each
  `| ... |` row and skips `-` (no-observation) rows; header + separator rows are
  ignored; empty text -> `[]`.
- **`durations_from_cycles_out`** — derives per-cycle durations from consecutive
  `========== CYCLE N <HH:MM:SS>Z ==========` start markers (the gap between
  consecutive starts); empty when fewer than two start markers.

## Impact
A regression in any parser (wrong column index, a `-` row counted as an
observation, a `done` marker misread as a start, a missing-marker crash) silently
corrupts the sizing verdict. Pinning each parser directly catches it.

## Suggestion
Add unit tests for each parser in `tests/test_wall_sizing.py`: the seed-dialect
positive case and the `None`/empty negative case for each. For
`durations_from_fourseer` pin the observed-plus-dash row and the
header/separator-ignored case. For `durations_from_cycles_out` pin the
consecutive-start gap (1420s), the single-marker -> `[]`, and the no-marker ->
`[]` cases.
