# TICKET-032: No committed fixture for the fourseer taxonomy dialect

## Evidence

The seed defines two fourseer output dialects:

- seed/fourseer-report-sample.txt — Per-Cycle Metrics table (Cycle / Outcome / Steps / Duration (s) / Trajectory).
- seed/fourseer-taxonomy-sample.txt — Failure-Mode Taxonomy:

    # Failure-Mode Taxonomy (2 cycles)

    cycles: 2
    modes: task_complete=2
    gates: -
    merged: -

The project has a committed fixture for the report dialect (tests/fixtures/fourseer-report.txt) but no fixture for the taxonomy dialect. No test in tests/ references "taxonomy" (verified: grep -rn "taxonomy" tests/ returns zero matches).

The seed SEED.md (line 18) explicitly lists the taxonomy file: "fourseer-taxonomy-sample.txt — real fourseer taxonomy output (failure modes)." The prerequisites check (prerequisites.py, line ~155) probes for fourseer importability but does not parse taxonomy output. However, the seed dialect caveat implies the taxonomy is part of the fourseer surface that a tool "consuming cycle data" may encounter.

## Impact

If a future cycle adds taxonomy parsing (e.g. to fold failure-mode counts into the report header or to detect a gates: - / merged: - signal), there is no committed fixture to pin the dialect against. The taxonomy format is simple but has specific field names (cycles:, modes:, gates:, merged:) and a dash-for-absent convention that must be pinned.

## Suggestion

1. Add tests/fixtures/fourseer-taxonomy.txt carrying the seed taxonomy dialect (matching seed/fourseer-taxonomy-sample.txt structure).
2. Add a variant fixture with non-trivial values (e.g. gates: 2, merged: 1, multiple modes).
3. Add a smoke test in test_wall_sizing.py (or a new test_fourseer.py) that reads the fixture and asserts the file is non-empty and contains the expected field names, pinning the dialect for future parsers.
