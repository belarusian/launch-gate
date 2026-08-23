# TICKET-019: endpoint-contention edge (m) IPv6 / bracketed host:port — bracketed-IPv6 overlap never matches (false GO) and a bare-IPv6 FIVE_* endpoint crashes the check

## Evidence
Two distinct defects in the IPv6 path, both reproduced end-to-end through
`check_endpoint_contention`:

1. **Bracketed-IPv6 overlap never matches (false GO).** `endpoint_hostport`
   (`endpoint_contention.py:90-106`) derives the host via `urlparse(url).hostname`,
   which STRIPS the brackets: `endpoint_hostport("http://[::1]:8080/v1")` →
   `'::1:8080'`. But `parse_ss` (`endpoint_contention.py:259-296`) keeps the
   brackets verbatim: an ESTAB line `tcp ESTAB 0 0 [::1]:8080 [::1]:51235
   users:(("node",pid=9999,fd=7))` → `SocketLine(local_hostport='[::1]:8080',
   pid=9999, process='node')`. In `scan_socket` (`endpoint_contention.py:312-315`)
   the match is `line.local_hostport not in target_hostports`, i.e.
   `'[::1]:8080' in {'::1:8080'}` → `False`, so the foreign pid 9999 is skipped.
   Reproduced: a driver targeting `http://[::1]:8080/v1` with a foreign ESTAB
   line on `[::1]:8080` returns **`go=True`** (false GO) with no NO-GO line.
   The same bracket mismatch also defeats the registry path: a registry
   `endpoints` entry written as `http://[::1]:8080/v1` is compared by raw-string
   equality against the script's endpoint, so it only matches if both sides use
   identical bracketing — and the socket fallback (the documented safety net)
   can never catch it.

2. **Bare-IPv6 (no brackets) FIVE_* endpoint crashes the check.** A driver that
   writes the endpoint without brackets, e.g.
   `export FIVE_BASE_URL="${FIVE_BASE_URL:-http://::1:8080/v1}"`, makes
   `endpoint_hostport` raise `ValueError: Port could not be cast to integer
   value as ':1:8080'` (from `parsed.port` inside `urlparse`). Reproduced: the
   `ValueError` propagates OUT of `check_endpoint_contention`, so the whole gate
   aborts instead of emitting a verdict.

## Impact
- A foreign process holding a bracketed-IPv6 endpoint is reported as GO — a
  direct violation of the "never guess occupancy" contract (a real contention is
  silently missed).
- A bare-IPv6 endpoint turns a deterministic GO/NO-GO gate into an unhandled
  exception (exit 2 / traceback), breaking the exit-code contract and the
  deterministic-report guarantee.
- Both are invisible to the current suite: `tests/test_endpoint_contention.py`
  only exercises IPv4 host:ports (`192.168.1.161:8080`).

## Suggestion
- Normalize host:port to a single canonical form on BOTH sides. Either (a) keep
  brackets in `endpoint_hostport` (use `urlparse(url).netloc` and strip a
  leading/trailing `]`/`[`-less port, or parse the netloc manually) so it
  matches `parse_ss`'s bracketed local address, or (b) strip brackets in
  `parse_ss` so it matches `urlparse.hostname`. Pick ONE canonical form and apply
  it to both the registry-overlap comparison and the socket match.
- Make `endpoint_hostport` total: handle a bare-IPv6 netloc (no brackets) by
  splitting on the LAST `:` (port) and treating the remainder as the host, and
  return a stable `host:port` (bracket the host if it contains `:`).
- Add tests to `tests/test_endpoint_contention.py`: bracketed-IPv6 URL →
  `endpoint_hostport` returns the same string `parse_ss` yields for the matching
  ESTAB line; a bracketed-IPv6 foreign socket line → NO-GO (not false GO); a
  bare-IPv6 FIVE_* endpoint → `check_endpoint_contention` returns a verdict
  (no exception). Do NOT shell out to real `ss`.
