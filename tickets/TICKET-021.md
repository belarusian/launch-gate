# TICKET-021: pin endpoint-contention edge (o) `outer_wall_seconds` / `launched_at` type-coercion defaults and freshness math

## Evidence
Cycle 6 pinned edges (h)-(k) but did not pin the type-coercion edge the brief
names:

- **(o) type-coercion defaults** — in `_parse_registry_file`
  (`endpoint_contention.py:123-130`):
  - `outer_wall_seconds`: `int(data.get("outer_wall_seconds",
    DEFAULT_OUTER_WALL_SECONDS))` wrapped in `try/except (TypeError, ValueError)`
    → missing or non-numeric falls back to `DEFAULT_OUTER_WALL_SECONDS` (7200).
    Reproduced: missing → 7200, `"abc"` → 7200, `12.7` → 12 (int-truncated),
    `3600` → 3600.
  - `launched_at`: `int(data.get("launched_at", 0))` with the same guard →
    missing or non-numeric falls back to `0`. Reproduced: missing → 0, `"abc"`
    → 0, `1234` → 1234.
  - **Freshness math uses the coerced wall and the file mtime, not
    `launched_at`.** `scan_registry` (`endpoint_contention.py:178-179`) computes
    `age = now - entry.mtime` and `fresh = age < entry.outer_wall_seconds`. The
    `launched_at` field is parsed and stored on `RegistryEntry` but is NOT used
    in the freshness decision — only `mtime` (the file's mtime) and the coerced
    `outer_wall_seconds` are. This is the honest, observable signal (a stale
    heartbeat file has an old mtime), and the pin must lock that in.

## Impact
A registry entry with a missing or garbage `outer_wall_seconds` must default to
the 7200s wall (not crash, not be treated as 0 → always-stale, not as
`inf` → always-fresh). Without pinning (o), a regression that (a) crashes on a
non-numeric wall, (b) defaults a missing wall to 0 (making every entry stale),
or (c) switches freshness to `launched_at` (which a driver may omit or set to a
wrong epoch) is invisible. The existing tests always write a well-formed integer
`outer_wall_seconds` and `launched_at`.

## Suggestion
Add tests to `tests/test_endpoint_contention.py`:
- a registry file with `outer_wall_seconds` missing and with `"abc"` → the
  freshness line reports `wall 7200s` (assert the exact line, e.g. a fresh
  foreign entry at `age 100s < wall 7200s` → NO-GO, and a stale entry at
  `age 10000s >= wall 7200s` → GO note).
- a registry file with `launched_at` missing / non-numeric → no crash, and the
  verdict is driven by `mtime` (assert the same line as when `launched_at` is a
  valid int, proving `launched_at` does not affect freshness).
Reuse the Cycle-5/6 helpers (`_write_registry` with a wall override, `NOW`,
`TARGET`). Do NOT shell out to real `ss`.
