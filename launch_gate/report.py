"""Deterministic, human-readable rendering of a launch-gate report.

This module is the **Reporting** layer. It turns a :class:`~launch_gate.models.Report`
(header + ordered per-check results) into a stable multi-line string that the CLI
prints verbatim. Everything here is a pure function: no I/O, no global state, and
byte-identical output for identical input so reports are reproducible.
"""

from __future__ import annotations

from launch_gate.models import Report

#: Width of the verdict column in the per-check table.
_VERDICT_WIDTH: int = 6


def render_report(report: Report) -> str:
    """Render a :class:`Report` as a deterministic multi-line string.

    Layout:
        1. A header block (what was checked, sources read).
        2. A per-check verdict table: each check's name, its GO/NO-GO verdict,
           and its indented evidence lines.
        3. A final ``ALL-GO`` / ``NO-GO`` line.

    Args:
        report: The report to render.

    Returns:
        A multi-line string (no trailing newline). Pure and deterministic:
        identical input yields byte-identical output.
    """
    lines: list[str] = []
    lines.append("launch-gate report")
    lines.append("=" * 40)
    for header_line in report.header:
        lines.append(header_line)
    lines.append("")
    lines.append("per-check verdicts")
    lines.append("-" * 40)
    for check in report.checks:
        verdict = check.label
        lines.append(f"{check.name:<20} {verdict}")
        for evidence in check.lines:
            lines.append(f"    {evidence}")
    lines.append("-" * 40)
    lines.append("ALL-GO" if report.all_go else "NO-GO")
    return "\n".join(lines)
