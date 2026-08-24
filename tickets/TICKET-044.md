# TICKET-044 — tests: run_checks ordering + all-GO/no-GO byte-exact goldens + determinism

## Capability
Add the missing contract tests:
1. A `run_checks` ordering test asserting the four check names come back in the
   stable `CHECK_ORDER` order.
2. A byte-exact golden report for BOTH an all-GO and a no-GO report (today only
   a no-GO golden exists in `tests/test_golden_report.py`).
3. A determinism test that two `run(..., now=fixed)` calls are byte-identical.

## Evidence (verified against code)
- `grep -rn "ordering\|CHECK_ORDER" tests/` -> no `run_checks` ordering test.
- `tests/test_golden_report.py` has `GOLDEN_REPORT` (a no-GO report: endpoint-
  contention NO-GO) + `test_render_report_matches_golden_byte_for_byte` +
  `test_golden_is_deterministic` + `test_run_checks_report_is_byte_identical_for_
  fixed_now`. There is NO all-GO byte-exact golden.
- `tests/test_report.py` has layout tests (`test_header_block_is_rendered`,
  `test_per_check_verdict_table_layout`, `test_final_line_all_go`,
  `test_final_line_no_go`) but these assert individual lines, not a full
  byte-exact all-GO golden.
- The determinism test exists at the `run_checks` level
  (`test_run_checks_report_is_byte_identical_for_fixed_now`); the brief asks for
  one at the `run(..., now=fixed)` level (the full CLI path).

## Impact
- The `run_checks` return order is a load-bearing contract (the report table
  rows are in that order) but is not asserted anywhere; a reorder would not be
  caught.
- An all-GO report has no byte-exact golden, so a layout regression that only
  manifests in the all-GO path (e.g. the final line) is under-pinned.
- The full `run(..., now=fixed)` path is not pinned for byte-identity.

## Suggestion
- Add `tests/test_checks_ordering.py` (or extend an existing file):
  `run_checks(...)` returns a tuple whose `[c.name for c in checks] ==
  CHECK_ORDER` (import from `launch_gate.checks`).
- Add an all-GO byte-exact golden to `tests/test_golden_report.py`
  (`GOLDEN_REPORT_ALL_GO` + a test), mirroring the existing no-GO golden.
- Add a determinism test that two `run([...], now=fixed)` calls (with a
  subprocess-free `git_state` injected) render byte-identical reports.
- Deterministic: inject `now`, `git_state`, `tool_available`; no real clock, no
  git shell-out, no live `ss`.

## Acceptance
- `run_checks` ordering test passes and references `CHECK_ORDER`.
- Both all-GO and no-GO byte-exact goldens pass.
- A `run(..., now=fixed)` determinism test passes (byte-identical).
