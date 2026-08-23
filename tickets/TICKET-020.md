# TICKET-020: pin endpoint-contention edge (n) registry entry with a non-list `endpoints` field is ignored (not a crash)

## Evidence
Cycle 6 pinned edges (h)-(k) but did not pin the malformed-`endpoints` edge the
brief names:

- **(n) non-list `endpoints`** — a registry file whose `endpoints` field is a
  string, number, or `null` (instead of a list) must be treated as "no
  endpoints" and ignored, not crash. Verified against `_parse_registry_file`
  (`endpoint_contention.py:120-122`): `endpoints = data.get("endpoints", [])`
  followed by `if not isinstance(endpoints, list): endpoints = []`. Reproduced
  for `endpoints` = string / number / `null` / dict: each yields
  `entry.endpoints == ()` (no crash), and `scan_registry` then reports
  `registry <project> does not target a checked endpoint; ignored.` with
  `go=True`, `covered=True`. The entry is still counted as "registry consulted"
  (`covered=True`) even though it matches nothing.

## Impact
A driver that writes a malformed registry (e.g. `endpoints` as a bare URL string
or `null`) must not crash the gate and must not be mistaken for occupancy.
Without pinning (n), a regression that (a) crashes on a non-list `endpoints`, or
(b) treats a non-list `endpoints` as a single-element list (false NO-GO) is
invisible. The existing `test_malformed_registry_file_is_go` only covers a
non-JSON file, not a valid-JSON file with a wrong-typed `endpoints` field.

## Suggestion
Add tests to `tests/test_endpoint_contention.py` writing a valid-JSON registry
file with `endpoints` set to a string, a number, and `null` (one test per shape
or a parametrized test). Assert `go is True`, `covered is True`, and the exact
`registry <project> does not target a checked endpoint; ignored.` line, and that
no exception is raised. Reuse the Cycle-5/6 helpers (`_write_registry` with an
`endpoints` override, `NOW`, `TARGET`).
