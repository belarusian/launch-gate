# TICKET-009 — redirect-safety: pin remaining edge cases (Cycle 4)

**Capability:** check 1 (`launch_gate/redirect_safety.py`) — sweep the edge
cases the Cycle-3 dedicated tests did not pin and pin them with unit tests.
Fix only if a case misclassifies (none do; all classify correctly).

## Edges to pin (assert `go` AND exact `lines`)
- (a) `1> cycles.out` (explicit-stdout fd) = truncate → NO-GO against a
  marker-bearing `cycles.out`; GO when there is no history.
- (b) `>> cycles.out` with NO existing history = GO (first launch, append safe).
- (c) a launch line that redirects to a DIFFERENT file (`> other.log`) = GO
  (nothing to gate — only `cycles.out` is gated).
- (d) whitespace variants (`>  cycles.out`, `>>cycles.out` no space) classify
  the same as the spaced forms.
- (e) a marker line that is NOT the seed dialect (e.g. `### CYCLE 1`) is NOT
  treated as a marker — only the `========== CYCLE N ==========` dialect counts.

## Files
- `tests/test_redirect_safety.py` (add tests)
- `launch_gate/redirect_safety.py` (fix only if misclassifying)

## Acceptance
`pytest tests/test_redirect_safety.py -x -q` green; `go` + exact `lines` asserted.
