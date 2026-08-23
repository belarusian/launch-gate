# TICKET-003: Missing `launch_gate/checks/` package and `run_checks(...)` orchestration

## Title
The target contract calls for a `launch_gate/checks/` package exposing a Check
result type plus a `run_checks(...)` orchestration that returns the four named
checks. Neither exists in the baseline.

## Evidence
- `ls launch_gate/checks` -> `No such file or directory`. There is no `checks/`
  subpackage; the four checks live as flat top-level modules:
  `launch_gate/redirect_safety.py`, `launch_gate/endpoint_contention.py`,
  `launch_gate/wall_sizing.py`, `launch_gate/prerequisites.py`.
- `grep -rn "run_checks" launch_gate/` -> no matches. There is no
  `run_checks(...)` orchestration function anywhere in the package.
- The Check result type is currently `CheckResult` in `launch_gate/models.py`
  (not in a `checks/` package), and the four checks are invoked ad hoc inside
  `launch_gate/cli.py:_run_check` (lines 149-162) rather than through a shared
  `run_checks(...)` entry point.

## Impact
The public surface does not match the documented target. Consumers that expect
`from launch_gate.checks import Check, run_checks` (or the four named checks
returned by `run_checks`) cannot import them. The orchestration logic is
duplicated/hidden inside the CLI instead of being a reusable, testable unit.

## Suggestion
- Introduce a `launch_gate/checks/` package (with `__init__.py`) that exposes the
  Check result type and a `run_checks(...)` function returning the four named
  checks (redirect-safety, endpoint-contention, wall-sizing, prerequisites) in a
  stable order.
- Either move the four check modules under `launch_gate/checks/` or re-export
  them from the package; keep `launch_gate/__init__.py`'s `__all__` in sync.
- Refactor `cli.py:_run_check` to call `run_checks(...)` so the CLI and any
  library consumer share one orchestration path.
- Mark exact public names (e.g. `Check` vs `CheckResult`) as TBD until the
  contract is pinned, and document them in `docs/API.md`.
