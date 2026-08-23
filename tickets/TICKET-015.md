# TICKET-015: pin endpoint-contention edges (h) ss-file precedence + (i) pid-lineage attribution

## Evidence
Cycle 5 pinned cases (a)-(g) in `tests/test_endpoint_contention.py` but did not
pin the remaining edges the brief names:

- **(h) `--ss-file` precedence** — when a readable `ss_file` is supplied, its
  text is used and live `ss` is NOT consulted (the "socket snapshot read from
  --ss-file <name>." line appears, never "live `ss -tnp`"); when `ss_file` is
  `None` or not a file, live `ss` is the fallback. Verified against
  `check_endpoint_contention`: the `ss_file.is_file()` branch reads the file and
  only falls through to `run_ss()` when `ss_text is None`.
- **(i) pid-lineage attribution** — a target host:port with MULTIPLE ESTAB lines
  where one pid is in the lineage and another is foreign = NO-GO (the foreign one
  wins); an empty `driver_lineage` set means every attributable pid is foreign;
  the `driver_lineage=None` default behaves as the empty set (`lineage =
  driver_lineage or set()`).

## Impact
These edges are the core of the "never guess" socket-fallback contract. Without
pinning them, a regression that consults live `ss` when a `--ss-file` is present,
or that treats a foreign pid as lineage (or vice-versa), is invisible.

## Suggestion
Add one test per edge (h) and (i) to `tests/test_endpoint_contention.py`,
asserting `go` AND exact `lines`. Reuse the Cycle-5 helpers (`_empty_registry`,
`_ss_file`, `NOW`, `TARGET`, `HOSTPORT`). For (h) patch `run_ss`
(`mock.patch.object(ec, "run_ss", ...)`) to assert it is NOT called when a
readable `ss_file` is present and IS called when it is not. For (i) add a
committed `ss` fixture with two ESTAB lines on the target port (one lineage pid,
one foreign pid). Do NOT shell out to real `ss`.
