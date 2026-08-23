# TICKET-028: pin wall-sizing (q) — no --script + no observations

## Evidence
`check_wall_sizing(None, ai_dir, project_dir)` in `launch_gate/wall_sizing.py`
with an empty `ai_dir`/`project_dir` (no fourseer report, no `cycles.out`)
returns GO with the conservative-default note. Verified at runtime (Cycle 9) the
exact `lines`:
- `no --script supplied; cannot parse the outer wall.`
- `no observed inner-pass durations found (no fourseer Duration, no cycles.out timestamps).`
- `conservative default row applies; GO with no observations.`

This is the no-`--script` counterpart of case (c) (which supplies a script). The
no-script + no-observations path is not pinned.

## Impact
A regression in the no-script branch (e.g. emitting the script-parsed lines, or
dropping the conservative-default note) would change the documented behavior for
the common "inspect artifacts only, no driver script" invocation. Pinning the
exact `lines` keeps it honest.

## Suggestion
Add a test in `tests/test_wall_sizing.py` using `tmp_path`: call
`check_wall_sizing(None, _empty_ai_dir(tmp_path), <empty proj>)` and assert
`go is True` AND the exact three `lines`.
