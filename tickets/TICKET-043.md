# TICKET-043 — cli: pin the usage-error + --help exit-code contract with tests

## Capability
Confirm and pin the CLI usage-error contract: a missing subcommand, an
unrecognized subcommand, and a missing required `--project-dir`/`--ai-dir` must
each yield exit code 2 with a clear stderr message and no escaping exception,
and `--help` must exit 0. The runtime behavior is already correct (verified);
the gap is the missing `--help` exit-0 test and the absence of a dedicated
usage-error contract test file.

## Evidence (verified against code + runtime)
- `launch_gate/cli.py` `run()` catches `SystemExit` from `parser.parse_args`
  and maps `code is None` -> 0, else `int(code)`; argparse exits 2 on a usage
  error and 0 on `--help`. Verified at runtime: `--help` -> 0, no-subcommand ->
  2, unrecognized -> 2, missing `--project-dir` -> 2, missing `--ai-dir` -> 2.
- `tests/test_cli.py` already has `test_exit_2_no_subcommand`,
  `test_exit_2_unrecognized_subcommand`, `test_exit_2_missing_project_dir`,
  `test_exit_2_missing_ai_dir` (each asserts `rc == 2` and `captured.err != ""`).
- `grep -rn "help" tests/test_cli.py` -> no `--help` exit-0 test exists.

## Impact
- The `--help` exit-0 half of the contract is untested; a regression that made
  `--help` exit non-zero (or raised) would not be caught.
- The usage-error tests assert `captured.err != ""` but not that the message is
  *clear* (mentions the offending token / flag); a regression to an empty or
  opaque stderr would still pass.

## Suggestion
- Add `test_help_exits_0` to `tests/test_cli.py`: `run(["--help"])` returns 0
  and stdout contains the subcommand usage (argparse writes help to stdout).
- Strengthen the three usage-error tests to assert the stderr message names the
  offending token/flag (e.g. `frobnicate` for the unrecognized subcommand,
  `--project-dir`/`--ai-dir` for the missing-flag cases) and that no exception
  escapes (the call returns an int, which is already implied).
- No `launch_gate/` code change expected (behavior already correct); this is a
  pinning ticket. If a probe reveals a real escaping exception or wrong code,
  harden `run()`.

## Acceptance
- `run(["--help"])` -> 0, help text on stdout.
- The three usage-error paths -> 2, clear stderr naming the token/flag, no
  exception.
- All existing exit-code tests still pass.
