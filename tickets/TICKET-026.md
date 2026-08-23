# TICKET-026: pin wall-sizing (o) — multiple fourseer reports (sorted-first selection)

## Evidence
`_find_fourseer_report(ai_dir)` in `launch_gate/wall_sizing.py` returns
`candidates[0]` where `candidates` is `sorted(...)` over every `*fourseer*report*`
file under `ai_dir` (recursive). Verified at runtime (Cycle 9): with
`fourseer-report-a.txt`, `fourseer-report-b.txt`, `zzz-fourseer-report.txt`, and a
nested `sub/fourseer-report-nested.txt` all present, the returned path is
`fourseer-report-a.txt` (lexicographically first).

Only `test_find_fourseer_report_found` (single file), `_absent_is_none`, and
`_non_dir_is_none` are pinned. The multi-file sorted-first selection is untested.

## Impact
A regression in the selection (e.g. switching to `rglob` order, picking the last
candidate, or a non-deterministic `sorted` tie-break) would silently read a
different fourseer report and change the observed durations, flipping the sizing
verdict. Deterministic selection is the whole point of the `sorted(...)` call.

## Suggestion
Add a test in `tests/test_wall_sizing.py` using `tmp_path`: create several
`*fourseer*report*` files (including one in a nested subdir) and assert
`_find_fourseer_report` returns the lexicographically first path.
