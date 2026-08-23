# TICKET-022: no dedicated tests/test_wall_sizing.py + fixtures; pin cases (a)-(f)

## Evidence
`tests/` has no `test_wall_sizing.py`. Check 3 (wall-sizing, B1) is only covered
incidentally (if at all) via `test_cli.py`/`test_report.py`. The brief requires a
dedicated file: one test per case (a)-(f), asserting `go` AND exact `lines`,
using `tmp_path` for `ai_dir`/`project_dir`, injecting `script_text`, and NOT
shelling out or touching the real clock.

The classification matrix to pin (verified against the seed dialects):
- **(a)** a fourseer `Duration (s)` observation (1358s) with a 10800s outer wall
  -> `10800 >= 3 * 1358 = 4074` -> GO.
- **(b)** the same observation with a 1000s outer wall -> `1000 < 4074` -> NO-GO.
- **(c)** no observations (no fourseer Duration, no cycles.out timestamps) -> GO
  with the conservative-default note.
- **(d)** an observation exists but no `--script` (no outer wall) -> NO-GO
  ("cannot verify sizing").
- **(e)** a cycles.out-derived observation (1420s) with a 10800s outer wall ->
  `10800 >= 3 * 1420 = 4260` -> GO.
- **(f)** the same cycles.out observation with a 1000s outer wall -> `1000 < 4260`
  -> NO-GO.

## Impact
Without dedicated tests a future regression in wall-sizing (a wrong multiplier, a
swapped GO/NO-GO, a mis-sorted observations line, a missing source note) is
invisible.

## Suggestion
Add `tests/test_wall_sizing.py` + tiny committed fixtures: a fourseer report with
a `Duration (s)` table (one observed row = 1358, one `-` row), a `cycles.out`
with 2+ timestamped start markers (14:27:19Z -> 14:50:59Z = 1420s) and a `done`
marker, and a driver script carrying the `perl -e 'alarm shift; exec @ARGV' 10800`
outer wall + `--inner-seconds 3000`. Pin (a)-(f) exactly. Synthesize original
fixture files; never copy the seed.
