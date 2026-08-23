# TICKET-034: No committed gate-log dialect fixtures (Results/Lessons table variants)

## Evidence

The seed SEED.md (lines 22-24) explicitly warns:

    Gate-log dialects drift between projects (### Results vs | Area | Status |
    tables, **Lessons:** vs ### Lessons). Parsers must tolerate variants and
    stay honest about what they could not parse.

The seed gate-log-sample.md shows one dialect:

    ### Results
    | Check | Result |
    |---|---|
    | pytest tests/ -x -q | 33 passed |
    ...
    ### Lessons
    1. **The four spokes need...**

The project has no gate-log fixture in tests/fixtures/ (verified: ls tests/fixtures/ shows no file with "gate" or "log" in its name). The prerequisites check (prerequisites.py) only tests file existence and non-emptiness — it does not parse gate-log content. However, the seed dialect caveat implies that a tool "consuming cycle data" may need to parse gate-log structure (e.g. extracting the Build Order table, detecting cycle status, reading Results/Lessons).

The actual gate log at ai/cycle-001-launch-gate-gate.md (36 KB, 10 cycles) carries the full dialect with ### What We Did, ### Results tables, ### Lessons sections, and ### Post-merge verification blocks. No committed fixture pins any of these variants.

## Impact

1. If a future cycle adds gate-log parsing (e.g. to extract the Build Order table for the report header, or to detect ## Cycle N: INCOMPLETE notes for the prerequisites check), there is no committed fixture to pin the dialect against.
2. The seed explicit dialect-drift warning (### Results vs | Area | Status |, **Lessons:** vs ### Lessons) means at least two variants must be pinned. Without fixtures, a parser that handles one variant would silently fail on the other.
3. The ## Cycle N: INCOMPLETE - <branch> + what remains> note (from the standing rules in launch-setup.sh) is a Phase-0 signal that the prerequisites check should report. No fixture pins this dialect.

## Suggestion

1. Add tests/fixtures/gate-log_results_table.md — a gate-log excerpt using the ### Results + | Check | Result | table dialect (matching the seed sample).
2. Add tests/fixtures/gate-log_area_status.md — a variant using the | Area | Status | table dialect (the other variant the seed warns about).
3. Add tests/fixtures/gate-log_incomplete.md — a gate-log excerpt containing a ## Cycle N: INCOMPLETE - build3/wall-sizing + outer wall parse regex note.
4. Add a smoke test in test_prerequisites.py that reads these fixtures and asserts the files are non-empty (pinning them for future parsers). If/when gate-log parsing is added, the tests should assert the exact parsed structure for each dialect variant.
