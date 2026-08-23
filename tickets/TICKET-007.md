# TICKET-007: No dedicated unit tests for check 1 (redirect-safety) — cases a-e + 2>/2>&1 edge unpinned

## Title
`launch_gate/redirect_safety.py` (check 1) has no dedicated test file. The
append-vs-bare-`>` classification against the `cycles.out` marker dialect is
only incidentally referenced in `tests/test_report.py` and `tests/test_cli.py`
(as canned `CheckResult` fixtures), so the real classification logic is
unpinned.

## Evidence
- `ls tests/` shows `test_cli.py`, `test_golden_report.py`, `test_report.py`,
  `test_smoke.py`, `__init__.py`. There is no `tests/test_redirect_safety.py`.
- `tests/test_report.py` and `tests/test_cli.py` only construct
  `CheckResult("redirect-safety", ...)` by hand; they never call
  `check_redirect_safety(...)` or `has_cycle_markers(...)`.
- `grep -rn "check_redirect_safety\|has_cycle_markers" tests/` -> no matches.
- The Cycle 3 brief requires one test per case (a)-(e) asserting both the `go`
  verdict AND the exact evidence lines, using the seed marker dialect for the
  "carries markers" fixture.

## Impact
The classification logic in `redirect_safety.py` (the `_redirect_to_cycles`
regex and the marker-aware GO/NO-GO matrix) can regress undetected. The `2>`
false-NO-GO bug (TICKET-006) is exactly the kind of regression this gap lets
through: nothing pins the edge cases.

## Suggestion
Add `tests/test_redirect_safety.py` with one test per case, each asserting
`result.go` and the exact `result.lines`:
- (a) `>>` to `cycles.out` = GO (append preserves history).
- (b) bare `>` with NO existing `cycles.out` (`cycles_out_text=None`) = GO
  (first launch).
- (c) bare `>` against an existing `cycles.out` carrying
  `========== CYCLE N ==========` markers = NO-GO. Use the seed marker dialect
  (a tiny committed fixture, e.g. `tests/fixtures/cycles_out_markers.txt`, or an
  inline string matching `seed/cycles.out.sample`).
- (d) bare `>` against an existing `cycles.out` with NO markers = GO
  (treated as first-launch history).
- (e) a launch line that does not redirect into `cycles.out` = GO.
- edge: `2> cycles.out` is NOT a truncate (see TICKET-006); `2>&1` is not a
  redirect into `cycles.out`.
Also unit-test `has_cycle_markers` directly (marker line present vs absent).
Keep the module pure and the tests stdlib-only.

---
GitHub issue: https://github.com/belarusian/launch-gate/issues/8
Closes #8
