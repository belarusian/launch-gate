# TICKET-014: no dedicated tests/test_endpoint_contention.py + fixtures; pin cases (a)-(g)

## Evidence
`tests/` has no `test_endpoint_contention.py`. Check 2 is only covered
incidentally (if at all) via `test_cli.py`/`test_report.py`. The brief
requires a dedicated file: one test per case (a)-(g) plus
`parse_endpoints`/`endpoint_hostport`/`parse_ss` unit tests, asserting `go`
AND exact `lines`, using `tmp_path` for registry dirs + ss files, injecting
`now` and `driver_lineage`, and NOT shelling out to real `ss`.

## Impact
The two real bugs (TICKET-012/013) went uncaught because nothing pinned the
classification matrix. Without dedicated tests a future regression in
endpoint contention is invisible.

## Suggestion
Add `tests/test_endpoint_contention.py` + tiny committed fixtures
(driver script with FIVE_* exports, fresh foreign registry JSON, stale
registry JSON, an `ss -tnp` snapshot with an ESTAB line on a target port
owned by a foreign pid). Pin (a)-(g) exactly.
