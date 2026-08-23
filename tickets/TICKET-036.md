# TICKET-036: No golden test pins the documented check-command contract (exact parser flags + exit codes)

## Evidence

The README "The check command" documents:

    launch-gate check <launch-line> --project-dir <proj> --ai-dir <ai> \
        [--script <driver.sh>] [--ss-file <file>]

with `<launch-line>` a positional, `--project-dir` + `--ai-dir` REQUIRED,
`--script` + `--ss-file` optional, no user-facing `--now` flag, and the exit-code
contract `0` = all-GO, `1` = any-NO-GO, `2` = usage error.

`launch_gate/cli.py` `build_parser()` + `run()` implement exactly this (verified by
introspecting the parser: positional `launch_line`; `--project-dir`/`--ai-dir`
required=True; `--script`/`--ss-file` required=False; no `--now`). `tests/test_cli.py`
pins the exit codes (0/1/2) but does NOT pin the *exact flag set* — a future drift
(adding a flag, making a required flag optional, or adding a `--now` flag) would not
be caught.

## Impact

A future README/code drift in the check-command surface (an invented flag, a required
flag shown as optional, a wrong exit code) would pass the gate silently.

## Suggestion

Add a golden contract test that introspects `build_parser()` and asserts: the only
subcommand is `check` (required); the positional is `launch_line`; the flag set is
exactly `{--project-dir, --ai-dir, --script, --ss-file}`; `--project-dir`/`--ai-dir`
required, `--script`/`--ss-file` optional; no `--now`. Reuse the existing exit-code
tests for the 0/1/2 contract. No subprocess, no real clock.
