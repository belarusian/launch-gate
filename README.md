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

1. **redirect-safety** — classifies how the launch line redirects into
   `cycles.out` and gates against the existing history:
   - `>> cycles.out` (append) is always GO — it preserves history.
   - a bare `>` / `1> cycles.out` (truncate) is NO-GO when the existing
     `cycles.out` carries a `========== CYCLE N ==========` marker line
     (it would wipe the history); it is GO when there is no history file
     (first launch) or the file has no markers yet.
   - a line that does not redirect into `cycles.out` (no redirect, a
     redirect to a *different* file, `2> cycles.out` stderr-only, or
     `2>&1`) is GO — nothing to gate.
   The marker dialect is the seed's `========== CYCLE N  <utc> ==========`
   (4+ equals, `CYCLE`, a number); a `========== CYCLE N done ==========`
   line also counts. Whitespace between `>` and `cycles.out` is tolerated.
2. **endpoint-contention** — never guesses occupancy; every verdict is
   backed by a concrete source (a registry entry or a socket line) or an
   explicit "no occupancy data" note. The classification matrix:
   - **Endpoint parse** — the target endpoints are the `FIVE_*` URL(s)
     parsed out of the `--script` driver (trailing `}`/`"`/punctuation
     stripped, de-duplicated, order-preserving). With no `--script`
     (`script_text=None`) or a script with no `FIVE_*` URLs, the check is
     GO with an honest "no occupancy data" note and no registry/socket
     scan at all.
   - **Registry scan (authoritative)** — scans `~/.four/launches/*.json`.
     A **fresh** entry (mtime within its own `outer_wall_seconds`, default
     7200) that lists a target endpoint and belongs to a *different*
     project is NO-GO (naming the occupying project); a fresh entry for
     *this* project is GO (not contention); a **stale** entry (age >= wall)
     is GO with a note; a malformed file is skipped (not counted). When the
     registry dir is non-empty, its verdict is **authoritative** and the
     socket fallback is skipped entirely (no `ss` call).
   - **Socket fallback** — only when the registry does not cover the target
     endpoints. The snapshot is a readable `--ss-file` when supplied, else
     live `ss -tnp` (the `--ss-file` is never consulted when it is not a
     file). An established connection on a target `host:port` owned by a pid
     **outside** the checked driver's lineage is NO-GO; a pid in the lineage
     is GO (not contention); a line with no attributable pid is GO with an
     honest "cannot confirm foreign ownership" note. With multiple
     established lines on a target port, a single foreign pid makes it
     NO-GO (the foreign one wins). An empty lineage set (or the `None`
     default) treats every attributable pid as foreign. The target
     `host:port` is canonicalized (IPv6 hosts bracketed, e.g.
     `[::1]:8080`; a bare-IPv6 endpoint is canonicalized the same way)
     so it matches the socket line's local address.
   - **No occupancy data** — no registry coverage and no socket snapshot
     (no live `ss`, no `--ss-file`) is GO with an explicit "no occupancy
     data" note.
3. **wall-sizing (B1)** — the outer wall (the `perl -e 'alarm shift; exec @ARGV' <wall>` seconds) must be large enough to contain the inner passes. Observed inner-pass durations come from two sources, combined:
   - **fourseer report** — the `Duration (s)` column (the 4th cell of each Per-Cycle Metrics row); a `-` in that cell means no observation and the row is skipped.
   - **`cycles.out`** — the gap between consecutive `========== CYCLE N  <utc> ==========` start markers approximates that cycle's wall time; fewer than two start markers yields no durations.
   - **Verdict** — with observations, `outer_wall >= 3 * max_observed` is GO, else NO-GO (naming the required `3 * max_observed` value).
   - **Observations but no outer wall** — no `--script` (or a script with no perl-alarm wall) means there is no outer wall to compare against -> NO-GO ("cannot verify sizing").
   - **No observations** — GO with a note that the conservative default row applies.
4. **prerequisites** — verifies the launch prerequisites:
   - a runner prompt and a gate log exist and are non-empty in `ai/`
     (found by a substring match over the directory: `runner-prompt`/`runner`
     and `gate`/`cycle`, first match in sorted order wins);
   - the checkout is a git repo on `main`, with a clean tree and `main` in
     sync with `origin/main` (a missing `origin/main` is a note, not NO-GO);
   - stranded `build*` branches are reported as a Phase-0 note (not NO-GO);
   - `fourseer` / `spoke_lint` / `loop_doctor` are probed in that fixed order
     and reported honestly as importable (verdict folded in) or not available.

## Report layout

The report is a deterministic, byte-stable multi-line string with three parts:

1. **Header block** — the title, a `=` rule, the header lines (what was
   checked, sources read), and a blank line.
2. **Per-check verdict table** — a `per-check verdicts` title, a `-` rule, then
   one row per check (name left-justified to 20 columns + the `GO`/`NO-GO`
   token) with each evidence line indented four spaces, and a closing `-` rule.
3. **Final line** — `ALL-GO` when every check is GO, else `NO-GO`.

A representative snippet (a NO-GO on endpoint-contention):

    launch-gate report
    ========================================
    launch line: nohup ./run.sh 3 4 >> cycles.out 2>&1 &
    project dir: /home/u/proj (project 'proj')

    per-check verdicts
    ----------------------------------------
    redirect-safety      GO
        launch line appends (>>) to cycles.out.
    endpoint-contention  NO-GO
        target endpoints: http://192.168.1.161:8080/v1.
        NO-GO: other holds http://192.168.1.161:8080/v1 (fresh, age 12s < wall 7200s, pid 4242).
    wall-sizing          GO
        outer wall (perl alarm): 21600s.
    prerequisites        GO
        on branch main.
    ----------------------------------------
    NO-GO

The exact bytes are pinned by the golden tests (`tests/test_golden_report.py`);
the layout widths are named constants in `launch_gate/report.py`.

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
    {"project": "$(basename "$PROJ")", "pid": "$$", "endpoints": ["$FIVE_BASE_URL", "$FIVE_LARGE_URL"], "outer_wall_seconds": $OUTER_WALL, "launched_at": $(date +%s)}
    JSON
    }
    write_registry
    trap 'rm -f "$REG_FILE"' EXIT
    # ... at the start of every cycle: write_registry   # heartbeat

## Gate

    pytest tests/ -x -q
    ruff check launch_gate/
    mypy launch_gate/ --ignore-missing-imports
