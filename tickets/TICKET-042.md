# TICKET-042 — report: pin the layout contract + add render_header helper

## Capability
Pin the report layout contract in `launch_gate/report.py` so the exact column
widths, separator lines, and the ALL-GO/NO-GO final line are named constants
(not inline literals), and add a small `render_header(...)` helper. Keep it
pure + deterministic.

## Evidence (verified against code)
- `launch_gate/report.py` line 14-15: only `_VERDICT_WIDTH: int = 6` is named;
  the per-check name column width `20` is an inline literal in
  `f"{check.name:<20} {verdict}"` (line ~40), and the separator widths
  `"=" * 40` / `"-" * 40` are inline literals (lines ~28, ~33, ~42).
- `grep -rn "render_header" launch_gate/ tests/` -> no matches (no helper).
- The title string `"launch-gate report"` and the section title
  `"per-check verdicts"` are inline literals.

## Impact
- The layout is pinned by tests (`tests/test_report.py`,
  `tests/test_golden_report.py`) but the *source* of the widths is scattered
  inline literals; a future change to one width requires editing the literal
  and the tests in lockstep with no single named constant to point at.
- No `render_header` helper means the header block (title + rule + header
  lines + blank line) is inlined in `render_report`; a caller that wants just
  the header cannot reuse it.

## Suggestion
- In `launch_gate/report.py`:
  - Add named constants: `_TITLE = "launch-gate report"`,
    `_RULE_WIDTH = 40`, `_NAME_WIDTH = 20`, `_SECTION_TITLE =
    "per-check verdicts"`, `_EVIDENCE_INDENT = "    "`, and keep
    `_VERDICT_WIDTH`.
  - Add `def render_header(header: Sequence[str]) -> list[str]` (or `str`)
    returning the title + `"=" * _RULE_WIDTH` + each header line + a blank
    line.
  - Refactor `render_report` to use the constants and `render_header`; the
    rendered bytes MUST be byte-identical to today (the golden test pins this).
- Deterministic: no I/O, no clock. Pure string building.

## Acceptance
- `render_report` output is byte-identical to before (golden test still passes).
- `render_header` exists and is pure; `render_report` composes it.
- The column widths / separators / final line are named constants.
