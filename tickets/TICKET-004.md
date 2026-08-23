# TICKET-004: Test suite is missing (report renderer, CLI exit codes, usage-error, golden report)

## Title
The test suite only contains a smoke test; the required coverage for the report
renderer, CLI exit-code contract (0/1/2), usage-error handling, and a
deterministic golden report is absent.

## Evidence
`ls tests/` shows only `tests/__init__.py` and `tests/test_smoke.py`.
`tests/test_smoke.py` only asserts that the package imports, exposes
`__version__`, and that `build_parser()` returns a parser with
`prog == "launch-gate"`. There are no tests for:

- the report renderer (`launch_gate/report.py:render_report`) — no test pins the
  header / per-check verdict table / ALL-GO|NO-GO layout;
- the CLI exit-code contract — no test drives `launch_gate.cli.run` to assert
  `0` (all-GO), `1` (any-NO-GO), and `2` (usage error);
- usage-error handling — no test asserts that a missing subcommand, an
  unrecognized subcommand, or a missing required `--project-dir`/`--ai-dir`
  yields exit code `2` with a stderr message and no escaping exception;
- a deterministic golden report — no test captures a full rendered report for a
  fixed input and asserts byte-identical output.

## Impact
The exit-code contract (0/1/2) and the deterministic report are load-bearing for
later automation, yet nothing pins them. A regression in `render_report` or in
`run`'s error path would ship undetected.

## Suggestion
Add tests under `tests/`:
- `test_report.py` — unit-test `render_report` for header, per-check table, and
  the final ALL-GO/NO-GO line; assert the exact layout for a fixed `Report`.
- `test_cli.py` — drive `launch_gate.cli.run([...])` (in-process) to assert exit
  codes `0`, `1`, and `2`; cover the usage-error paths (no subcommand, bad
  subcommand, missing required args) and assert a stderr message is emitted and
  no exception escapes.
- `test_golden_report.py` — build a fixed `Report` (or a fixed set of check
  inputs) and assert `render_report` output equals a committed golden string
  byte-for-byte.
- Keep the suite stdlib-only and injectable (the checks already accept
  `git_state`/`tool_available`/`ss_file`/`now` so they are testable in-process).
