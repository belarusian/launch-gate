# TICKET-006: redirect-safety misclassifies a `2> cycles.out` (stderr-only) redirect as a truncate (false NO-GO)

## Title
Check 1 (`launch_gate/redirect_safety.py`) reads a stderr-only redirect
(`2> cycles.out`) as a bare truncate into `cycles.out`, producing a false
NO-GO against an existing marker file. The brief explicitly requires that
`2>` / `2>&1` must NOT be read as a truncate into `cycles.out`.

## Evidence
`launch_gate/redirect_safety.py:52` classifies a truncate with:

    if re.search(r"(?<!>)>\s*cycles\.out", launch_line):
        return "truncate"

The comment at `redirect_safety.py:50-51` claims this matches a `>` "not part
of `2>`/`2>&1`", but the negative lookbehind `(?<!>)` only excludes a
preceding `>` — it does NOT exclude a preceding digit. So `2> cycles.out`
matches: the `>` is preceded by `2`, not by `>`.

Reproduced in-process (marker file = `seed/cycles.out.sample`):

    check_redirect_safety('nohup ./run.sh 3 4 2> cycles.out &', marker)
      -> go=False, lines=('launch line uses bare (>) redirect against an existing cycles.out.',
                          'existing cycles.out carries cycle markers; bare (>) would truncate history.')

A stderr-only redirect does not truncate the stdout history that the cycle
markers live in, so this should be GO (or at least not a truncate). The
`2>&1` case is already handled correctly (verified: `... 2>&1 &` -> "does not
redirect into cycles.out; nothing to gate."). Only the `2>` form is wrong.

## Impact
A driver that appends stdout to `cycles.out` but sends stderr to a separate
file (or to `cycles.out` via `2>`) is wrongly gated NO-GO on a continuation
launch. This is a false negative in the safety gate — it blocks a legitimate
launch and contradicts the documented semantics in the module docstring
(`redirect_safety.py:1-11`) and the Cycle 3 brief.

## Suggestion
- Extend the truncate regex to also exclude a preceding digit (and the
  `&`-form), e.g. `(?<![0-9>])>\s*cycles\.out`, so `2> cycles.out` is not
  classified as a truncate. Keep `>>` (append) and the bare stdout `>`
  classification unchanged.
- Add a dedicated unit test pinning the `2> cycles.out` edge (see
  TICKET-007) asserting it is NOT classified as a truncate into `cycles.out`.
- Re-run `pytest tests/ -x -q`, `ruff check launch_gate/`, and
  `mypy launch_gate/ --ignore-missing-imports`.

---
GitHub issue: https://github.com/belarusian/launch-gate/issues/7
Closes #7
