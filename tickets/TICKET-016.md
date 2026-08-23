# TICKET-016: pin endpoint-contention edge (j) registry `covered` semantics + (k) no --script / no FIVE_* endpoints

## Evidence
Cycle 5 pinned cases (a)-(g) but did not pin:

- **(j) registry `covered` semantics** — when the registry dir is non-empty
  (`reg_covered` True), the registry verdict is AUTHORITATIVE and the socket
  fallback is SKIPPED entirely (no "falling back to socket snapshot." line, no
  `run_ss` call): a fresh-foreign registry is NO-GO even if a socket snapshot
  would also be NO-GO, and a stale-only registry is GO with no socket line.
  Verified: `check_endpoint_contention` returns immediately after `scan_registry`
  when `reg_covered` is True, before the socket-fallback block.
- **(k) no `--script` / no FIVE_* endpoints** — `script_text=None` and a script
  with no FIVE_* URLs both GO with the honest "no occupancy data" note (no
  registry/socket scan at all). Verified: both early-return before any
  `scan_registry`/`scan_socket` call.

## Impact
The authoritative-registry short-circuit and the never-guess no-data note are the
two honesty guarantees of check 2. A regression that still runs the socket
fallback after a covered registry (or that scans when there is no script) would
silently change the verdict and the evidence lines.

## Suggestion
Add one test per edge (j) and (k) to `tests/test_endpoint_contention.py`,
asserting `go` AND exact `lines`. For (j) patch `run_ss` and assert it is NOT
called (the socket fallback is skipped) for both the fresh-foreign (NO-GO) and
stale-only (GO) covered registries. For (k) assert the two distinct no-occupancy
notes and that no registry/socket line appears.
