# TICKET-005: Report is not deterministic — wall-clock `now` leaks into rendered output

## Title
The "deterministic text report" contract is violated: the current wall-clock
time is read at runtime and its derived value is rendered into the report body,
so two runs of the same inputs can produce different bytes.

## Evidence
- `launch_gate/cli.py:137` — `now = time.time()` is captured at run time.
- `launch_gate/cli.py:156` — `now` is passed to `check_endpoint_contention(...)`.
- `launch_gate/endpoint_contention.py:185` — `age = now - entry.mtime`.
- `launch_gate/endpoint_contention.py:190` and `:200` — the derived age is
  formatted into evidence lines that are rendered verbatim:
  `f"NO-GO: {entry.project} holds {overlap[0]} (fresh, age {int(age)}s < ..."` and
  `f"registry {entry.project} targets {overlap[0]} but is stale (age {int(age)}s >= ...)"`.

Because `now` advances between runs, `int(age)` changes, so the rendered report
bytes differ across runs even for identical inputs. This directly contradicts the
module docstring of `launch_gate/report.py` ("byte-identical output for identical
input so reports are reproducible") and the target's "deterministic golden report"
requirement (see TICKET-004).

## Impact
A golden-report test (TICKET-004) cannot pass deterministically while the report
embeds wall-clock-derived values. Reproducibility of the GO/NO-GO report — the
core promise of the tool — is not guaranteed.

## Suggestion
- Make `now` injectable into the CLI (e.g. a `--now` option or an internal
  parameter to `_run_check`) so tests can pin it; default to `time.time()` only
  at the outermost entry point.
- Alternatively, render the registry age as a stable, coarse value (or omit the
  exact seconds) so the report is stable for a given registry snapshot.
- Pin the chosen approach in `docs/API.md` and add a golden-report test that
  asserts byte-identical output for a fixed `now`.
