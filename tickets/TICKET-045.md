# TICKET-045 — README: add a short "Report layout" section

## Capability
Add a short "Report layout" section to `README.md` showing the three parts of
the rendered report (header block / per-check verdict table / ALL-GO-NO-GO
final line), and verify the check-command example matches the actual CLI.

## Evidence (verified against code)
- `grep -n "Report layout" README.md` -> no such section.
- `launch_gate/report.py` `render_report` layout: title `"launch-gate report"`
  + `"=" * 40` rule + header lines + blank line + `"per-check verdicts"` +
  `"-" * 40` rule + per-check rows (`name` left-justified to 20 cols + GO/NO-GO
  token, evidence indented 4 spaces) + `"-" * 40` rule + final `ALL-GO`/`NO-GO`
  line.
- The README "The check command" example already matches `build_parser()`
  (positional `launch_line`; `--project-dir`/`--ai-dir` required; `--script`/
  `--ss-file` optional) — verified in Cycle 11; re-confirm only.

## Impact
- The report layout is a load-bearing, byte-pinned contract (golden tests) but
  is not documented in the README; a reader cannot see the header / table /
  final-line structure without reading the source.

## Suggestion
- Add a `## Report layout` section (after "The four checks" or near the Gate)
  with a short fenced example showing: the title + `=` rule + header lines, the
  `per-check verdicts` `-` rule + a couple of `name  GO`/`name  NO-GO` rows with
  indented evidence, the closing `-` rule, and the final `ALL-GO`/`NO-GO` line.
  Keep it short (a representative snippet, not the full golden).
- Re-confirm the check-command example matches the CLI (no change expected).

## Acceptance
- README has a "Report layout" section showing header / per-check table /
  ALL-GO-NO-GO line.
- The check-command example still matches the actual CLI.
