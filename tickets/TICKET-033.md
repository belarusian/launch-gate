# TICKET-033: Registry fixtures incomplete — missing fresh-own and malformed variants; existing fixtures orphaned

## Evidence

The seed endpoint-contention spec (SEED.md, launch-setup.sh goal text) defines four registry states:

| State | Expected verdict |
|---|---|
| Fresh, foreign project | NO-GO (naming the occupying project) |
| Fresh, own project | GO (not contention) |
| Stale (age >= wall) | GO with a note |
| Absent (no registry file) | Fall through to socket fallback |

Committed fixtures in tests/fixtures/:

- registry_fresh_foreign.json — fresh, foreign project. Used by no test (verified: grep -rn "registry_fresh_foreign" tests/*.py returns zero matches; tests construct registry files inline via _write_registry).
- registry_stale.json — stale entry. Used by no test (same grep result).

Missing committed fixtures:
- Fresh, own project — a registry entry whose project field matches the checked project name. This is the GO/not-contention case.
- Malformed JSON — a registry file that is not valid JSON (or has a non-list endpoints field). The inline test test_non_list_endpoints_field_is_ignored_without_crash (test_endpoint_contention.py, line ~590) covers this but constructs the file inline.
- Absent — no registry file at all. This is tested via _empty_registry(tmp_path) but has no committed fixture (an empty directory is not a file fixture).

The two existing fixture files (registry_fresh_foreign.json, registry_stale.json) are orphaned: they exist on disk but are not referenced by any test. They were likely intended as committed regression fixtures but the tests were written to construct registry files inline instead.

## Impact

1. The orphaned fixtures are dead weight: they document the dialect but are not exercised by the test suite. A change to the registry JSON schema (e.g. renaming outer_wall_seconds) would not break any test via these fixtures.
2. The fresh-own-project case (GO, not contention) has no committed fixture. This is the most common production case (a driver re-launching itself) and the one most likely to regress silently.
3. The malformed-JSON case has no committed fixture, so the "skip malformed files" behavior is only pinned by inline test construction.

## Suggestion

1. Add tests/fixtures/registry_fresh_own.json — a fresh entry whose project matches the checked project (e.g. "project": "myproj").
2. Add tests/fixtures/registry_malformed.json — a file with invalid JSON content (e.g. {not valid json).
3. Wire the existing registry_fresh_foreign.json and registry_stale.json into tests: add tests in test_endpoint_contention.py that read these files from FIXTURES, set their mtime via os.utime, and assert the exact verdict + lines.
4. Add a test that reads registry_fresh_own.json and asserts GO (not contention) when the project name matches.
5. Add a test that reads registry_malformed.json and asserts the file is skipped (no crash, no false NO-GO).
