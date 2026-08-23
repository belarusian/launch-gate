# TICKET-010 — prerequisites: pin remaining edge cases (Cycle 4)

**Capability:** check 4 (`launch_gate/prerequisites.py`) — sweep the edge cases
the Cycle-3 dedicated tests did not pin and pin them with unit tests. Fix only
if a case misclassifies (none do).

## Edges to pin (assert `go` AND exact `lines`)
- (a) the file-matching heuristic — a runner prompt named `*-runner-prompt*.md`
  and a gate log named `*gate*.md` are found; a subdirectory (not a file) is
  skipped; the `cycle` substring fallback finds a gate log.
- (b) when BOTH runner prompt and gate log are missing, BOTH NO-GO lines appear
  in order (runner first, then gate).
- (c) the no-origin note line is present AND the verdict stays GO (re-confirm).
- (d) multiple stranded build branches are all listed in one note.
- (e) the tool fold-in order is stable (fourseer, spoke_lint, loop_doctor).

## Files
- `tests/test_prerequisites.py` (add tests)
- `launch_gate/prerequisites.py` (fix only if misclassifying)

## Acceptance
`pytest tests/test_prerequisites.py -x -q` green; `go` + exact `lines` asserted.
