# TICKET-024: pin the wall-sizing artifact discovery (_find_fourseer_report, _find_cycles_out)

## Evidence
The two discovery helpers in `launch_gate.wall_sizing` are not unit-tested:

- **`_find_fourseer_report(ai_dir)`** — returns the first `*fourseer*report*`
  file under `ai_dir` (sorted), or `None` when absent / `ai_dir` is not a dir.
- **`_find_cycles_out(ai_dir, project_dir)`** — returns a `cycles.out` under
  `ai_dir` first, then `project_dir`, or `None` when absent.

## Impact
A regression in discovery (a wrong name match, a non-dir crash, `project_dir`
checked before `ai_dir`, or a missing file raising instead of returning `None`)
silently drops the observation source and flips the sizing verdict. Pinning both
helpers catches it.

## Suggestion
Add unit tests in `tests/test_wall_sizing.py` using `tmp_path`: fourseer found /
absent / non-dir; cycles.out found in `ai_dir`, found in `project_dir` (when
`ai_dir` has none), and absent. Assert the returned path's name and the `None`
cases.
