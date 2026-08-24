"""Deterministic, human-readable rendering of a launch-gate report.

This module is the **Reporting** layer. It turns a :class:`~launch_gate.models.Report`
(header + ordered per-check results) into a stable multi-line string that the CLI
prints verbatim. Everything here is a pure function: no I/O, no global state, and
byte-identical output for identical input so reports are reproducible.

The layout contract is pinned by named constants (see :data:`_TITLE`,
:data:`_RULE_WIDTH`, :data:`_NAME_WIDTH`, :data:`_SECTION_TITLE`,
:data:`_EVIDENCE_INDENT`, :data:`_VERDICT_WIDTH`) so the exact column widths and
separator lines have a single source of truth. The golden tests
(``tests/test_golden_report.py``) pin the rendered bytes; the constants pin the
*source* of those bytes.
"""

from __future__ import annotations

from collections.abc import Sequence

from launch_gate.models import Report

#: The report title (first line of the header block).
_TITLE: str = "launch-gate report"

#: Width of the header rule (``"=" * _RULE_WIDTH``) and the per-check section
#: rules (``"-" * _RULE_WIDTH``).
_RULE_WIDTH: int = 40

#: Width of the per-check name column (left-justified).
_NAME_WIDTH: int = 20

#: The per-check verdict section title.
_SECTION_TITLE: str = "per-check verdicts"

#: The indent applied to each evidence line under a check's verdict.
_EVIDENCE_INDENT: str = "    "

#: Width of the verdict column in the per-check table.
_VERDICT_WIDTH: int = 6


def render_header(header: Sequence[str]) -> list[str]:
    """Render the report's header block as a list of lines.

    The header block is: the title, the ``"=" * _RULE_WIDTH`` rule, each header
    line verbatim, and a single trailing blank line. This is the first part of
    :func:`render_report`'s output, factored out so a caller that wants just the
    header can reuse it.

    Args:
        header: The header lines (what was checked, sources read).

    Returns:
        A list of lines (no trailing newline on any line). Pure and
        deterministic: identical input yields identical lines.
    """
    lines: list[str] = [_TITLE, "=" * _RULE_WIDTH]
    lines.extend(header)
    lines.append("")
    return lines


def render_report(report: Report) -> str:
    """Render a :class:`Report` as a deterministic multi-line string.

    Layout:
        1. A header block (what was checked, sources read) — see
           :func:`render_header`.
        2. A per-check verdict table: each check's name, its GO/NO-GO verdict,
           and its indented evidence lines.
        3. A final ``ALL-GO`` / ``NO-GO`` line.

    Args:
        report: The report to render.

    Returns:
        A multi-line string (no trailing newline). Pure and deterministic:
        identical input yields byte-identical output.
    """
    lines: list[str] = render_header(report.header)
    lines.append(_SECTION_TITLE)
    lines.append("-" * _RULE_WIDTH)
    for check in report.checks:
        verdict = check.label
        lines.append(f"{check.name:<{_NAME_WIDTH}} {verdict}")
        for evidence in check.lines:
            lines.append(f"{_EVIDENCE_INDENT}{evidence}")
    lines.append("-" * _RULE_WIDTH)
    lines.append("ALL-GO" if report.all_go else "NO-GO")
    return "\n".join(lines)
