# TICKET-037: No golden test pins the documented launch-registry block field set + semantics

## Evidence

The README "Canonical launch-registry block" documents exactly five JSON fields
(`project`, `pid`, `endpoints`, `outer_wall_seconds`, `launched_at`), the path
`~/.four/launches/<project>.json`, the default outer wall `7200`, and the
heartbeat/trap semantics. `launch_gate/endpoint_contention.py` implements:
`_parse_registry_file` (pid coerced to string; `outer_wall_seconds` defaults to
`DEFAULT_OUTER_WALL_SECONDS`=7200 when absent/non-numeric; `launched_at` defaults to
0), `scan_registry` (freshness = mtime + outer_wall, NOT launched_at), and
`cli._registry_dir()` = `~/.four/launches`.

`tests/test_endpoint_contention.py` pins the coercion defaults and mtime-based
freshness incidentally, but does NOT pin the *documented field set* (exactly the five
fields, in order) or the documented registry dir. A future drift (adding a field to
`RegistryEntry`, renaming one, or moving the registry dir) would not be caught.

## Impact

A future README/code drift in the registry-block surface (an invented field, a renamed
field, a moved registry path, a changed default wall) would pass the gate silently.

## Suggestion

Add a golden contract test that asserts: the `RegistryEntry` content fields (excluding
parser-added `path`/`mtime`) are exactly the five documented fields in the README's
order; a full block parses all five; pid is a string (numeric tolerated + coerced);
`outer_wall_seconds` defaults to 7200 (absent + non-numeric); `launched_at` defaults
to 0; freshness uses mtime not launched_at; and `_registry_dir()` == `~/.four/launches`.
No subprocess, no real clock (mtimes + now injected).
