# TICKET-002: Baseline fails `mypy` (has_cycle_markers arg-type str|None)

## Title
The launch_gate package does not pass the mypy gate; 1 arg-type error.

## Evidence
`python3 -m mypy launch_gate/ --ignore-missing-imports` reports:

- `launch_gate/redirect_safety.py:72` — error: Argument 1 to "has_cycle_markers"
  has incompatible type "str | None"; expected "str" [arg-type].

The offending line:
    has_markers = has_cycle_markers(cycles_out_text) if history_exists else False

`has_cycle_markers` is declared as `def has_cycle_markers(cycles_out_text: str) -> bool`
(`redirect_safety.py:24`), but `cycles_out_text` is typed `str | None` (the parameter
of `check_redirect_safety`, `redirect_safety.py:57`). The `if history_exists` guard
narrows the value at runtime, but mypy does not narrow the *other* variable
`cycles_out_text` from the boolean `history_exists` (which is `cycles_out_text is not None`).

## Impact
The documented gate (`mypy launch_gate/ --ignore-missing-imports`) fails, so the
package cannot be considered type-clean.

## Suggestion
Narrow the type explicitly so mypy accepts the call, e.g.
    has_markers = has_cycle_markers(cycles_out_text) if cycles_out_text is not None else False
or guard with `if cycles_out_text is not None:` before the call. Re-run mypy until
it reports no errors.
