# TICKET-025: pin wall-sizing (n) — ai/cycles.out subpath discovery

## Evidence
`_find_cycles_out(ai_dir, project_dir)` in `launch_gate/wall_sizing.py` probes
`("cycles.out", "ai/cycles.out")` under each of `ai_dir` then `project_dir`.
Verified at runtime (Cycle 9):
- `ai_dir/ai/cycles.out` is found when `ai_dir/cycles.out` is absent.
- `project_dir/ai/cycles.out` is found when `ai_dir` has no `cycles.out`.
- A top-level `cycles.out` in the same base wins over `ai/cycles.out` in that
  base (the `for name in (...)` loop checks `cycles.out` first).

None of these subpath behaviors are pinned. `test_find_cycles_out_in_ai_dir` and
`test_find_cycles_out_in_project_dir` only cover the top-level `cycles.out` in
each base; the `ai/cycles.out` subpath and the top-level-over-subpath precedence
are untested.

## Impact
A regression in the subpath probe (dropping the `ai/cycles.out` name, reordering
the `name` loop so the subpath shadows the top-level file, or checking
`project_dir` before `ai_dir`) silently changes which `cycles.out` is read and
can flip the sizing verdict. The seed dialect note (SEED.md) explicitly calls out
that some drivers write `cycles.out` at project root with no symlink, so the
subpath is a real-world seam.

## Suggestion
Add tests in `tests/test_wall_sizing.py` using `tmp_path`:
- `ai_dir/ai/cycles.out` found when `ai_dir/cycles.out` absent.
- `project_dir/ai/cycles.out` found when `ai_dir` has no `cycles.out`.
- top-level `cycles.out` wins over `ai/cycles.out` within the same base.
Assert the returned path (name and parent) for each.
