# TICKET-018: pin endpoint-contention edge (l) multi-endpoint overlap — a source covering only ONE of two distinct FIVE_* endpoints drives the verdict; the uncovered one is not silently dropped

## Evidence
Cycle 6 pinned edges (h)-(k) in `tests/test_endpoint_contention.py` but did not
pin the multi-endpoint overlap edge the brief names:

- **(l) multi-endpoint overlap** — a driver script can carry TWO distinct
  `FIVE_*` endpoints (e.g. `FIVE_BASE_URL=http://192.168.1.161:8080/v1` and
  `FIVE_LARGE_URL=http://192.168.1.162:9000/v1`). When a fresh-foreign registry
  entry (or a socket line) covers only ONE of the two, the verdict is driven by
  the covered one and the uncovered one is NOT silently dropped from the target
  list. Verified against `scan_registry` (`endpoint_contention.py:145-191`):
  `target_set = set(target_endpoints)` keeps BOTH endpoints; `overlap = [e for e
  in entry.endpoints if e in target_set]` matches only the covered one; the
  NO-GO line names `overlap[0]` (the covered endpoint); `covered` is `True`
  (registry consulted) even though the second endpoint has no registry coverage.
  Reproduced: targets `[E1, E2]`, registry covers only `E1` fresh-foreign →
  `go=False`, `covered=True`, single line
  `NO-GO: other holds http://192.168.1.161:8080/v1 (fresh, age 100s < wall 7200s, pid 4242).`
  The uncovered `E2` is absent from the evidence but was never dropped from the
  `target_set` used for matching.

## Impact
The "never guess" contract depends on the target list being the full set of
`FIVE_*` endpoints. Without pinning (l), a regression that (a) reduces the
target set to the first endpoint only, (b) treats a partial-overlap registry as
"no coverage" and falls through to the socket fallback, or (c) drops the
uncovered endpoint from the evidence is invisible. The existing tests only ever
use a single `TARGET` endpoint, so the multi-endpoint path is untested.

## Suggestion
Add tests to `tests/test_endpoint_contention.py` using a two-endpoint script
(`FIVE_BASE_URL` + `FIVE_LARGE_URL` with distinct host:ports). Pin, asserting
`go` AND exact `lines`:
- a fresh-foreign registry covering only endpoint 1 → NO-GO naming endpoint 1,
  `covered=True`, socket fallback skipped (patch `run_ss`, assert not called);
- a socket line on only endpoint 1 (empty registry) → NO-GO naming endpoint 1,
  endpoint 2 produces no line (not dropped, simply uncovered by the snapshot);
- a registry/socket covering only endpoint 2 → NO-GO naming endpoint 2.
Reuse the Cycle-5/6 helpers (`_empty_registry`, `_ss_file`, `NOW`). Do NOT shell
out to real `ss`.
