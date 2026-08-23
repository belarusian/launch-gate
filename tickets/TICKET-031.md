# TICKET-031: No committed fixture for the full seed cycles.out dialect (trajectory/outcome/git-status lines between markers)

## Evidence

The seed cycles.out.sample (12 cycles) shows the full production dialect between markers:

    ========== CYCLE 1  14:27:19Z ==========
    OUTER trajectory saved to: /home/sasha/AI/spoke-lint/ai/trajectories/trajectory_0004.json
    OUTER outcome: exit:task_complete
    On branch main
    Your branch is up to date with 'origin/main'.

    nothing to commit, working tree clean
    ========== CYCLE 1 done ==========

The committed fixtures are simplified:

- tests/fixtures/cycles.out (2 cycles): has OUTER trajectory saved to: and OUTER outcome: lines but no git-status block.
- tests/fixtures/cycles_out_long.out (4 cycles): same simplified form.
- tests/fixtures/cycles_out_markers.txt (1 line): only the marker line, no body.

The actual cycles.out at the repo root (10 cycles) carries the full dialect including the ./run-cycles.sh: line 77: ... Alarm clock ... perl -e 'alarm shift; exec @ARGV' 3600 python3 ... timeout lines (cycles 2 and 5). No committed fixture includes:
- The On branch main / Your branch is up to date / nothing to commit, working tree clean git-status block.
- The Alarm clock timeout line variant (a cycle that hit the outer wall).

## Impact

The durations_from_cycles_out parser (wall_sizing.py, line ~82) only reads the ========== CYCLE N <HH:MM:SS>Z ========== start-marker timestamps, so the body content does not affect wall-sizing. However, the has_cycle_markers function (redirect_safety.py, line ~22) scans all lines. A future parser that inspects cycle bodies (e.g. detecting timeout cycles, extracting trajectory paths) would have no committed fixture to pin against. The seed explicitly warns: "fourseer sees 0 cycles when ai/cycles.out is absent (some drivers write it at project root with no symlink). A tool consuming cycle data must state which source it read and what it could not find."

## Suggestion

1. Add tests/fixtures/cycles_out_full_dialect.out carrying 3+ cycles in the full seed dialect (trajectory line, outcome line, git-status block, done marker).
2. Add a variant fixture tests/fixtures/cycles_out_timeout.out with one cycle carrying the Alarm clock timeout line (matching the real cycles.out cycles 2 and 5).
3. Add tests in test_wall_sizing.py that read these fixtures and assert durations_from_cycles_out produces the correct durations (the body lines must not interfere with timestamp extraction).
4. Add a test in test_redirect_safety.py that has_cycle_markers returns True for the full-dialect fixture.
