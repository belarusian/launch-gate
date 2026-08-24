# TICKET-041 — checks: expose CHECK_ORDER + verdict_of, pin run_checks return order as a contract

## Capability
The CLI and the tests each re-derive "which checks ran, in what order, and is the
overall verdict GO" from the tuple returned by `run_checks`. Today that knowledge
lives only in a docstring. Add a machine-readable contract so the CLI and the
tests share one source of truth:

1. A `CHECK_ORDER` constant — the four stable check names in `run_checks` order.
2. A `verdict_of(checks) -> bool` helper — `True` iff every check is GO (all-GO).
3. The `run_checks` return order documented as an explicit contract (not just prose).

## Evidence (verified against code)
- `launch_gate/checks/__init__.py` line 25-29: `__all__ = ["Check", "CheckResult",
  "run_checks"]` — no `CHECK_ORDER`, no `verdict_of`.
- `launch_gate/checks/__init__.py` line 73-76: the return order
  (`redirect-safety`, `endpoint-contention`, `wall-sizing`, `prerequisites`) is
  stated only in the `Returns:` docstring prose, not as a constant.
- `grep -rn "CHECK_ORDER\|verdict_of" launch_gate/ tests/` → no matches.
- The all-GO verdict is currently computed two different ways:
  `launch_gate/cli.py` `_run_check` uses `report.all_go` (via `Report`), while a
  library caller of `run_checks` must re-implement `all(c.go for c in checks)`.
  `launch_gate/models.py` `Report.all_go` (line ~40) already encodes the rule
  `bool(checks) and all(c.go for c in checks)` — `verdict_of` should mirror it.

## Impact
- The CLI and any test that asserts "the four checks in stable order" must hard-code
  the four names and their order independently of `run_checks`. If the order ever
  changes, the constant and the docstring and the tests can silently diverge.
- No shared `verdict_of` means the all-GO rule is duplicated (in `Report.all_go`
  and ad-hoc in callers), risking a divergence between "all checks GO" and
  "report says ALL-GO".

## Suggestion
- In `launch_gate/checks/__init__.py`:
  - `CHECK_ORDER: tuple[str, ...] = ("redirect-safety", "endpoint-contention",
    "wall-sizing", "prerequisites")` — the exact names `run_checks` returns, in
    order.
  - `def verdict_of(checks: Sequence[CheckResult]) -> bool:` returning
    `bool(checks) and all(c.go for c in checks)` (mirror `Report.all_go`).
  - Add both to `__all__`.
  - In the `run_checks` `Returns:` docstring, reference `CHECK_ORDER` as the
    authoritative order (e.g. "in the order given by :data:`CHECK_ORDER`").
- Keep `run_checks` itself unchanged (it already returns in that order).
- Deterministic: no I/O, no clock. Pure data + a pure predicate.

## Acceptance
- `from launch_gate.checks import CHECK_ORDER, verdict_of` works.
- `CHECK_ORDER == ("redirect-safety", "endpoint-contention", "wall-sizing",
  "prerequisites")`.
- `verdict_of` returns `True` for an all-GO tuple, `False` for any-NO-GO, and
  `False` for the empty tuple (mirrors `Report.all_go`).
- `run_checks` return order is documented as a contract referencing `CHECK_ORDER`.
