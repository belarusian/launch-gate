# launch-gate

A deterministic, stdlib-only Python CLI that gates a four pipeline launch at the
launch moment — the gap between pre-launch readiness (loop-doctor) and the run.
It inspects driver artifacts and emits a deterministic GO/NO-GO report.

- Entrypoint: `python3 -m launch_gate` (also installed as `launch-gate`).
- Exit codes: `0` = all-GO, `1` = any-NO-GO, `2` = usage error.

## The check command

    launch-gate check <launch-line> --project-dir <proj> --ai-dir <ai> \
        [--script <driver.sh>] [--ss-file <file>]

`<launch-line>` is the driver invocation string, e.g.
`nohup ./run-cycles.sh 3 4 >> cycles.out 2>&1 &`. `--script` is the driver
script that invocation runs.

### Example on a real driver

    launch-gate check "nohup ./run-cycles.sh 3 4 >> cycles.out 2>&1 &" \
        --project-dir /home/sasha/AI/launch-gate/proj \
        --ai-dir /home/sasha/AI/launch-gate/ai \
        --script /home/sasha/AI/launch-gate/run-cycles.sh

## The four checks

1. **redirect-safety** — a continuation launch must append (`>>`) to `cycles.out`;
   a bare `>` against an existing marker file is NO-GO; a first launch is GO.
2. **endpoint-contention** — via the launch-registry (below), with a socket
   snapshot fallback. Never guesses occupancy.
3. **wall-sizing (B1)** — `outer_wall >= 3 * max_observed` inner-pass duration.
4. **prerequisites** — runner prompt + gate log present/non-empty; clean, synced
   main; optional fourseer/spoke-lint/loop-doctor verdicts folded in.

## Canonical launch-registry block (every four driver must carry)

Each four driver writes a heartbeat registry file at launch and removes it on
exit. Path: `~/.four/launches/<project>.json`. Content:

    {
      "project": "<name>",
      "pid": "<driver pid>",
      "endpoints": ["<FIVE_BASE_URL>", "<FIVE_LARGE_URL>"],
      "outer_wall_seconds": <N>,
      "launched_at": <epoch>
    }

The driver rewrites/touches it at the start of every cycle (heartbeat) and clears
it via `trap ... EXIT`. The canonical bash block:

    REG_DIR="$HOME/.four/launches"
    REG_FILE="$REG_DIR/$(basename "$PROJ").json"
    mkdir -p "$REG_DIR"
    write_registry() {
      cat > "$REG_FILE" <<JSON
    {"project": "$(basename "$PROJ")", "pid": $$, "endpoints": ["$FIVE_BASE_URL", "$FIVE_LARGE_URL"], "outer_wall_seconds": $OUTER_WALL, "launched_at": $(date +%s)}
    JSON
    }
    write_registry
    trap 'rm -f "$REG_FILE"' EXIT
    # ... at the start of every cycle: write_registry   # heartbeat

## Gate

    pytest tests/ -x -q
    ruff check launch_gate/
    mypy launch_gate/ --ignore-missing-imports
